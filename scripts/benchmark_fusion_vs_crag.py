from __future__ import annotations

import hashlib
import html
import os
import re
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

ROOT = Path('/home/ecode/Documents/projetos/projeto-rag')
CHROMA_PATH = ROOT / 'sources' / 'rag_memory' / '02 - RAG with memory' / 'chroma_db'
REPORT = ROOT / 'analises' / 'benchmark-fusion-vs-crag.md'


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


def search(client_chroma: chromadb.PersistentClient, model_emb: SentenceTransformer, collection: str, query: str, n_results: int = 8):
    col = client_chroma.get_collection(collection)
    q_emb = model_emb.encode([query]).tolist()
    out = col.query(query_embeddings=q_emb, n_results=n_results, include=['documents', 'distances'])
    docs = out['documents'][0]
    dists = out['distances'][0]
    return list(zip(docs, dists))


def generate_rewrites(client: OpenAI, model: str, question: str, n: int = 4) -> list[str]:
    prompt = (
        'Gere variacoes semanticas de consulta para busca RAG. '
        f'Crie {n} reformulacoes da pergunta abaixo, mantendo intencao. '
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


def fusion_search(client_chroma, model_emb, collection: str, question: str, rewrites: list[str], top_k: int = 8, per_query: int = 6):
    scores: dict[str, float] = {}
    docs_map: dict[str, str] = {}

    queries = [question] + rewrites
    for q in queries:
        ranked = search(client_chroma, model_emb, collection, q, n_results=per_query)
        for rank, (doc, _dist) in enumerate(ranked, start=1):
            h = _hash_text(doc)
            scores[h] = scores.get(h, 0.0) + (1.0 / rank)
            docs_map[h] = doc

    merged = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return [docs_map[h] for h, _ in merged]


def _clean_html(texto: str) -> str:
    sem_tags = re.sub(r'<[^>]+>', ' ', texto or '')
    sem_tags = html.unescape(sem_tags)
    return re.sub(r'\s+', ' ', sem_tags).strip()


def _normalize_ddg_url(url: str) -> str:
    url = (url or '').strip().strip("'\"")
    if not url:
        return ''
    if url.startswith('//'):
        url = 'https:' + url
    parsed = urlparse(url)
    if 'duckduckgo.com' in (parsed.netloc or '').lower():
        params = parse_qs(parsed.query)
        uddg = params.get('uddg', [])
        if uddg:
            destino = unquote(uddg[0]).strip().strip("'\"")
            if destino.startswith('//'):
                destino = 'https:' + destino
            return destino
    return url


def web_chunks_ddg(query: str, max_results: int = 4) -> list[str]:
    url = f'https://html.duckduckgo.com/html/?q={quote_plus(query)}'
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urlopen(req, timeout=10) as resp:
            page = resp.read().decode('utf-8', errors='ignore')
    except Exception:
        return []

    pattern = re.compile(
        r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    found = pattern.findall(page)
    chunks = []
    for href, title_html, snippet_html in found[:max_results]:
        link = _normalize_ddg_url(html.unescape(href))
        if 'duckduckgo.com' in link:
            continue
        title = _clean_html(title_html)
        snippet = _clean_html(snippet_html)
        chunk = f'Fonte web: {title}. Resumo: {snippet}. URL: {link}'
        chunks.append(chunk[:450])
    return chunks


def evaluate_action(client: OpenAI, model: str, question: str, chunks: list[str]) -> str:
    contexto = '\n\n'.join(chunks[:8]) if chunks else '(sem chunks)'
    prompt = f"""Você é um avaliador CRAG. Classifique se os chunks são suficientes para responder a pergunta.

Critérios:
- CORRECT: suficiente e direto
- AMBIGUOUS: parcialmente relevante, mas incompleto
- INCORRECT: insuficiente para responder

Pergunta:
{question}

Chunks:
{contexto}

Responda APENAS com uma palavra: CORRECT, AMBIGUOUS ou INCORRECT.
"""
    resp = client.chat.completions.create(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
    )
    raw = (resp.choices[0].message.content or '').upper()
    for tag in ('CORRECT', 'AMBIGUOUS', 'INCORRECT'):
        if tag in raw:
            return tag
    return 'AMBIGUOUS'


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
    actions_count = {'CORRECT': 0, 'AMBIGUOUS': 0, 'INCORRECT': 0}

    for case in CASES:
        # Fusion
        t_f0 = time.time()
        rewrites = generate_rewrites(llm, model, case.question, n=4)
        fusion_chunks = fusion_search(chroma, emb, case.collection, case.question, rewrites, top_k=8, per_query=6)
        t_f = time.time() - t_f0

        # CRAG (com base no baseline local da mesma colecao)
        t_c0 = time.time()
        baseline_local = [doc for doc, _dist in search(chroma, emb, case.collection, case.question, n_results=8)]
        action = evaluate_action(llm, model, case.question, baseline_local)
        actions_count[action] += 1

        web_chunks = []
        if action in ('AMBIGUOUS', 'INCORRECT'):
            web_chunks = web_chunks_ddg(case.question, max_results=4)

        if action == 'INCORRECT':
            crag_chunks = web_chunks[:8]
        elif action == 'AMBIGUOUS':
            crag_chunks = (baseline_local + web_chunks)[:8]
        else:
            crag_chunks = baseline_local[:8]

        t_c = time.time() - t_c0

        fset = {_hash_text(x) for x in fusion_chunks}
        cset = {_hash_text(x) for x in crag_chunks}

        overlap = len(fset & cset) / 8 if cset else 0.0
        novelty_crag_vs_fusion = len(cset - fset) / 8 if cset else 0.0
        web_ratio = min(len(web_chunks), 8) / 8

        rows.append(
            {
                'collection': case.collection,
                'question': case.question,
                'fusion_s': round(t_f, 2),
                'crag_s': round(t_c, 2),
                'action': action,
                'web_ratio': round(web_ratio, 2),
                'overlap': round(overlap, 2),
                'novelty_crag': round(novelty_crag_vs_fusion, 2),
                'rewrites': rewrites,
            }
        )

    avg_fusion = statistics.mean(r['fusion_s'] for r in rows)
    avg_crag = statistics.mean(r['crag_s'] for r in rows)
    avg_overlap = statistics.mean(r['overlap'] for r in rows)
    avg_novelty = statistics.mean(r['novelty_crag'] for r in rows)
    avg_web_ratio = statistics.mean(r['web_ratio'] for r in rows)

    lines = [
        '# Benchmark: RAG-Fusion vs CRAG (rodada 1)',
        '',
        '## Metodologia',
        '- Fusion: 4 reformulacoes via LLM + consulta original, fusao por ranking reciproco (top-8).',
        '- CRAG: busca local baseline (top-8) + avaliador LLM (CORRECT/AMBIGUOUS/INCORRECT).',
        '- Para AMBIGUOUS/INCORRECT: busca web via DuckDuckGo e recomposicao de contexto.',
        '',
        '## Resultado agregado',
        f'- Latencia media fusion: **{avg_fusion:.2f}s**',
        f'- Latencia media CRAG: **{avg_crag:.2f}s**',
        f'- Overlap medio@8 (fusion vs crag): **{avg_overlap:.2f}**',
        f'- Novelty media@8 do CRAG vs fusion: **{avg_novelty:.2f}**',
        f'- Proporcao media de chunks web no CRAG: **{avg_web_ratio:.2f}**',
        f"- Acoes do avaliador: CORRECT={actions_count['CORRECT']}, AMBIGUOUS={actions_count['AMBIGUOUS']}, INCORRECT={actions_count['INCORRECT']}",
        '',
        '## Resultado por colecao',
        '',
        '| Colecao | Fusion(s) | CRAG(s) | Acao | Web ratio | Overlap@8 | Novelty CRAG@8 |',
        '|---|---:|---:|---|---:|---:|---:|',
    ]

    for r in rows:
        lines.append(
            f"| `{r['collection']}` | {r['fusion_s']:.2f} | {r['crag_s']:.2f} | {r['action']} | {r['web_ratio']:.2f} | {r['overlap']:.2f} | {r['novelty_crag']:.2f} |"
        )

    lines.append('')
    lines.append('## Reformulacoes de exemplo (fusion)')
    for r in rows:
        lines.append(f"\n### {r['collection']}")
        for rw in r['rewrites']:
            lines.append(f'- {rw}')

    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(f'relatorio: {REPORT}')


if __name__ == '__main__':
    main()
