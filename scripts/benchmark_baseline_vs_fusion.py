from __future__ import annotations

import hashlib
import os
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

ROOT = Path('/home/ecode/Documents/projetos/projeto-rag')
CHROMA_PATH = ROOT / 'sources' / 'rag_memory' / '02 - RAG with memory' / 'chroma_db'
REPORT = ROOT / 'analises' / 'benchmark-baseline-vs-fusion.md'


@dataclass
class Case:
    collection: str
    question: str


CASES = [
    Case('sandeco_prompts_v1', 'Quais principios praticos ajudam a escrever bons prompts para tarefas tecnicas?'),
    Case('sandeco_guardrails_v1', 'Como aplicar guardrails para reduzir respostas fora do objetivo em agentes?'),
    Case('sandeco_python_ia_v1', 'Qual o papel do Python em pipelines de IA aplicada para iniciantes?'),
    Case('sandeco_crewai1_v1', 'No CrewAI basico, como agentes, tarefas e crews se conectam?'),
    Case('sandeco_crewai2_v1', 'No CrewAI intermediario, quais integracoes praticas sao mais comuns em automacoes?'),
    Case('sandeco_mcp_a2a_v1', 'Qual a diferenca entre MCP e A2A na arquitetura de agentes?'),
    Case('sandeco_rag_book_v1', 'Qual a diferenca entre RAG classico, CRAG e Agentic RAG?'),
    Case('sandeco_orange_v1', 'Como o Orange Canvas ajuda iniciantes em IA visual e ciencia de dados?'),
    Case('sandeco_deep_learning_v1', 'Quais fundamentos de deep learning sao mais importantes para comecar projetos?'),
]


def _hash_text(s: str) -> str:
    return hashlib.sha1(s.encode('utf-8', errors='ignore')).hexdigest()


def generate_rewrites(client: OpenAI, model: str, question: str, n: int = 4) -> list[str]:
    prompt = (
        'Gere variacoes semanticas de consulta para busca RAG. '
        f'Crie {n} reformulacoes da pergunta abaixo, mantendo intencao. '\
        'Responda somente com uma consulta por linha, sem numeracao.\n\n'
        f'Pergunta: {question}'
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
    )
    text = resp.choices[0].message.content or ''
    rewrites = [ln.strip('-• \t') for ln in text.splitlines() if ln.strip()]
    rewrites = [r for r in rewrites if len(r) > 5]
    return rewrites[:n]


def search(client_chroma: chromadb.PersistentClient, model_emb: SentenceTransformer, collection: str, query: str, n_results: int = 8):
    col = client_chroma.get_collection(collection)
    q_emb = model_emb.encode([query]).tolist()
    out = col.query(
        query_embeddings=q_emb,
        n_results=n_results,
        include=['documents', 'distances'],
    )
    docs = out['documents'][0]
    dists = out['distances'][0]
    return list(zip(docs, dists))


def fusion_search(client_chroma, model_emb, collection: str, question: str, rewrites: list[str], top_k: int = 8, per_query: int = 6):
    scores: dict[str, float] = {}
    docs_map: dict[str, str] = {}
    dists_map: dict[str, list[float]] = {}

    queries = [question] + rewrites
    for q in queries:
        ranked = search(client_chroma, model_emb, collection, q, n_results=per_query)
        for rank, (doc, dist) in enumerate(ranked, start=1):
            h = _hash_text(doc)
            scores[h] = scores.get(h, 0.0) + (1.0 / rank)
            docs_map[h] = doc
            dists_map.setdefault(h, []).append(float(dist))

    merged = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    results = []
    for h, score in merged:
        avg_dist = statistics.mean(dists_map[h]) if dists_map[h] else 0.0
        results.append((docs_map[h], avg_dist, score))
    return results


def main():
    load_dotenv(ROOT / '.env')
    api_key = os.getenv('OPENAI_API_KEY')
    model = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
    if not api_key:
        raise SystemExit('OPENAI_API_KEY nao encontrado em /home/ecode/Documents/projetos/projeto-rag/.env')

    llm = OpenAI(api_key=api_key)
    chroma = chromadb.PersistentClient(path=str(CHROMA_PATH))
    emb = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    rows = []

    for case in CASES:
        t0 = time.time()
        baseline = search(chroma, emb, case.collection, case.question, n_results=8)
        t_baseline = time.time() - t0

        t1 = time.time()
        rewrites = generate_rewrites(llm, model, case.question, n=4)
        fusion = fusion_search(chroma, emb, case.collection, case.question, rewrites, top_k=8, per_query=6)
        t_fusion = time.time() - t1

        bset = {_hash_text(d) for d, _ in baseline}
        fset = {_hash_text(d) for d, _, _ in fusion}
        inter = len(bset & fset)
        overlap = inter / 8
        novelty = len(fset - bset) / 8

        bdist = statistics.mean([float(d) for _, d in baseline]) if baseline else 0.0
        fdist = statistics.mean([float(d) for _, d, _ in fusion]) if fusion else 0.0

        rows.append({
            'collection': case.collection,
            'question': case.question,
            'baseline_s': round(t_baseline, 2),
            'fusion_s': round(t_fusion, 2),
            'overlap': round(overlap, 2),
            'novelty': round(novelty, 2),
            'baseline_dist': round(bdist, 4),
            'fusion_dist': round(fdist, 4),
            'rewrites': rewrites,
        })

    avg_baseline = statistics.mean(r['baseline_s'] for r in rows)
    avg_fusion = statistics.mean(r['fusion_s'] for r in rows)
    avg_overlap = statistics.mean(r['overlap'] for r in rows)
    avg_novelty = statistics.mean(r['novelty'] for r in rows)
    avg_bdist = statistics.mean(r['baseline_dist'] for r in rows)
    avg_fdist = statistics.mean(r['fusion_dist'] for r in rows)

    lines = [
        '# Benchmark: Baseline vs RAG-Fusion (rodada 1)',
        '',
        '## Metodologia',
        '- Baseline: 1 consulta por pergunta, top-8 no Chroma.',
        '- Fusion: 4 reformulacoes (LLM) + consulta original, fusao por Reciprocal Rank, top-8 final.',
        '- Embeddings: paraphrase-multilingual-MiniLM-L12-v2.',
        '',
        '## Resultado agregado',
        f'- Latencia media baseline: **{avg_baseline:.2f}s**',
        f'- Latencia media fusion: **{avg_fusion:.2f}s**',
        f'- Overlap medio@8 (baseline vs fusion): **{avg_overlap:.2f}**',
        f'- Novelty media@8 (novos chunks no fusion): **{avg_novelty:.2f}**',
        f'- Distancia media baseline (menor melhor): **{avg_bdist:.4f}**',
        f'- Distancia media fusion (menor melhor): **{avg_fdist:.4f}**',
        '',
        '## Resultado por colecao',
        '',
        '| Colecao | Baseline(s) | Fusion(s) | Overlap@8 | Novelty@8 | Dist baseline | Dist fusion |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]

    for r in rows:
        lines.append(
            f"| `{r['collection']}` | {r['baseline_s']:.2f} | {r['fusion_s']:.2f} | {r['overlap']:.2f} | {r['novelty']:.2f} | {r['baseline_dist']:.4f} | {r['fusion_dist']:.4f} |"
        )

    lines.append('')
    lines.append('## Reformulacoes usadas (amostra)')
    for r in rows:
        lines.append(f"\n### {r['collection']}")
        for rw in r['rewrites']:
            lines.append(f'- {rw}')

    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(f'relatorio: {REPORT}')


if __name__ == '__main__':
    main()
