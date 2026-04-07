from __future__ import annotations

import hashlib
import html
import json
import os
import random
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
REPORT_MD = ROOT / 'analises' / 'avaliacao-qualitativa-cega-rodada-6.md'
REPORT_JSON = ROOT / 'analises' / 'avaliacao-qualitativa-cega-rodada-6.json'


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
    out = col.query(query_embeddings=q_emb, n_results=n_results, include=['documents'])
    return out['documents'][0]


def generate_rewrites(client: OpenAI, model: str, question: str, n: int = 4) -> list[str]:
    prompt = (
        'Gere variacoes semanticas de consulta para busca RAG. '
        f'Crie {n} reformulacoes da pergunta abaixo, mantendo intencao. '
        'Responda somente com uma consulta por linha, sem numeracao.\n\n'
        f'Pergunta: {question}'
    )
    resp = client.chat.completions.create(model=model, messages=[{'role': 'user', 'content': prompt}])
    text = resp.choices[0].message.content or ''
    rewrites = [ln.strip('-• \t') for ln in text.splitlines() if ln.strip()]
    rewrites = [r for r in rewrites if len(r) > 5]
    return rewrites[:n]


def fusion_chunks(client_chroma, emb, collection: str, question: str, rewrites: list[str], top_k: int = 8, per_query: int = 6):
    scores: dict[str, float] = {}
    docs_map: dict[str, str] = {}
    for q in [question] + rewrites:
        docs = search(client_chroma, emb, collection, q, n_results=per_query)
        for rank, doc in enumerate(docs, start=1):
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
        chunks.append(f'Fonte web: {title}. Resumo: {snippet}. URL: {link}'[:450])
    return chunks


def eval_crag_action(client: OpenAI, model: str, question: str, chunks: list[str]) -> str:
    contexto = '\n\n'.join(chunks[:8]) if chunks else '(sem chunks)'
    prompt = f"""Classifique se os chunks abaixo bastam para responder a pergunta.
Responda APENAS com uma palavra: CORRECT, AMBIGUOUS ou INCORRECT.

Pergunta: {question}

Chunks:
{contexto}
"""
    resp = client.chat.completions.create(model=model, messages=[{'role': 'user', 'content': prompt}])
    raw = (resp.choices[0].message.content or '').upper()
    for tag in ('CORRECT', 'AMBIGUOUS', 'INCORRECT'):
        if tag in raw:
            return tag
    return 'AMBIGUOUS'


def answer_with_context(client: OpenAI, model: str, question: str, chunks: list[str]) -> str:
    ctx = '\n\n'.join(chunks[:8]) if chunks else '(sem contexto)'
    prompt = f"""Responda em pt-BR e markdown com base principal no contexto.
Se o contexto for insuficiente, declare limites de forma objetiva.

Pergunta:
{question}

Contexto:
{ctx}
"""
    resp = client.chat.completions.create(model=model, messages=[{'role': 'user', 'content': prompt}])
    return (resp.choices[0].message.content or '').strip()


def parse_json_block(text: str) -> dict:
    text = text.strip()
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if not m:
        return {}
    raw = m.group(0)
    try:
        return json.loads(raw)
    except Exception:
        # tentativa de limpeza simples
        raw = raw.replace("'", '"')
        try:
            return json.loads(raw)
        except Exception:
            return {}


def judge_blind(client: OpenAI, model: str, question: str, candidates: list[dict]) -> dict:
    blocos = []
    for c in candidates:
        blocos.append(f"[{c['label']}]\n{c['answer']}")
    joined = '\n\n'.join(blocos)

    prompt = f"""Voce e avaliador tecnico. Compare respostas sem saber o metodo.
Pergunta: {question}

Respostas:
{joined}

Rubrica (0 a 5):
- precisao
- cobertura
- clareza
- aderencia_contexto

Retorne APENAS JSON valido neste formato:
{{
  "scores": {{
    "A": {{"precisao": 0, "cobertura": 0, "clareza": 0, "aderencia_contexto": 0}},
    "B": {{"precisao": 0, "cobertura": 0, "clareza": 0, "aderencia_contexto": 0}},
    "C": {{"precisao": 0, "cobertura": 0, "clareza": 0, "aderencia_contexto": 0}}
  }},
  "ranking": ["A", "B", "C"],
  "comentario_curto": "..."
}}
"""
    resp = client.chat.completions.create(model=model, messages=[{'role': 'user', 'content': prompt}])
    text = resp.choices[0].message.content or '{}'
    return parse_json_block(text)


def total_score(s: dict) -> float:
    return float(s.get('precisao', 0)) + float(s.get('cobertura', 0)) + float(s.get('clareza', 0)) + float(s.get('aderencia_contexto', 0))


def main():
    load_dotenv(ROOT / '.env')
    api_key = os.getenv('OPENAI_API_KEY')
    model = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
    if not api_key:
        raise SystemExit('OPENAI_API_KEY nao encontrado em /home/ecode/Documents/projetos/projeto-rag/.env')

    llm = OpenAI(api_key=api_key)
    chroma = chromadb.PersistentClient(path=str(CHROMA_PATH))
    emb = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    results = []
    method_totals = {'baseline': [], 'fusion': [], 'crag': []}
    method_dims = {
        'baseline': {'precisao': [], 'cobertura': [], 'clareza': [], 'aderencia_contexto': []},
        'fusion': {'precisao': [], 'cobertura': [], 'clareza': [], 'aderencia_contexto': []},
        'crag': {'precisao': [], 'cobertura': [], 'clareza': [], 'aderencia_contexto': []},
    }
    rank_points = {'baseline': 0, 'fusion': 0, 'crag': 0}

    for case in CASES:
        t0 = time.time()
        base_chunks = search(chroma, emb, case.collection, case.question, n_results=8)
        rewrites = generate_rewrites(llm, model, case.question, n=4)
        fus_chunks = fusion_chunks(chroma, emb, case.collection, case.question, rewrites, top_k=8, per_query=6)

        action = eval_crag_action(llm, model, case.question, base_chunks)
        web = web_chunks_ddg(case.question, max_results=4) if action in ('AMBIGUOUS', 'INCORRECT') else []
        if action == 'INCORRECT':
            crag_chunks = web[:8]
        elif action == 'AMBIGUOUS':
            crag_chunks = (base_chunks + web)[:8]
        else:
            crag_chunks = base_chunks[:8]

        ans_base = answer_with_context(llm, model, case.question, base_chunks)
        ans_fus = answer_with_context(llm, model, case.question, fus_chunks)
        ans_crag = answer_with_context(llm, model, case.question, crag_chunks)

        candidates = [
            {'method': 'baseline', 'answer': ans_base},
            {'method': 'fusion', 'answer': ans_fus},
            {'method': 'crag', 'answer': ans_crag},
        ]

        rnd = random.Random(_hash_text(case.collection + case.question))
        rnd.shuffle(candidates)
        for i, c in enumerate(candidates):
            c['label'] = ['A', 'B', 'C'][i]

        judged = judge_blind(llm, model, case.question, candidates)
        scores = judged.get('scores', {}) if isinstance(judged, dict) else {}
        ranking = judged.get('ranking', []) if isinstance(judged, dict) else []

        label_to_method = {c['label']: c['method'] for c in candidates}
        per_method_scores = {'baseline': 0.0, 'fusion': 0.0, 'crag': 0.0}

        for label in ('A', 'B', 'C'):
            method = label_to_method.get(label)
            s = scores.get(label, {}) if isinstance(scores, dict) else {}
            if method:
                per_method_scores[method] = total_score(s)
                for k in ('precisao', 'cobertura', 'clareza', 'aderencia_contexto'):
                    method_dims[method][k].append(float(s.get(k, 0)))

        for m in ('baseline', 'fusion', 'crag'):
            method_totals[m].append(per_method_scores[m])

        for pos, label in enumerate(ranking[:3], start=1):
            method = label_to_method.get(label)
            if not method:
                continue
            # 1o=3 pts, 2o=2, 3o=1
            rank_points[method] += (4 - pos)

        elapsed = round(time.time() - t0, 2)
        results.append(
            {
                'collection': case.collection,
                'question': case.question,
                'action_crag': action,
                'web_chunks': len(web),
                'scores_total': per_method_scores,
                'ranking': ranking,
                'label_to_method': label_to_method,
                'judge_comment': judged.get('comentario_curto', '') if isinstance(judged, dict) else '',
                'elapsed_s': elapsed,
            }
        )

    avg_scores = {m: round(statistics.mean(vals), 2) if vals else 0.0 for m, vals in method_totals.items()}
    avg_dims = {
        m: {k: round(statistics.mean(v), 2) if v else 0.0 for k, v in dims.items()}
        for m, dims in method_dims.items()
    }
    avg_elapsed = round(statistics.mean(r['elapsed_s'] for r in results), 2)

    lines = [
        '# Avaliacao qualitativa cega - rodada 6',
        '',
        '## Metodo',
        '- Tres metodos comparados por pergunta: baseline, fusion e crag.',
        '- Para cada pergunta, respostas foram embaralhadas (A/B/C) antes da avaliacao.',
        '- Juiz LLM aplicou rubrica 0-5 em: precisao, cobertura, clareza e aderencia ao contexto.',
        '',
        '## Resultado agregado',
        f"- Score medio total baseline: **{avg_scores['baseline']:.2f}/20**",
        f"- Score medio total fusion: **{avg_scores['fusion']:.2f}/20**",
        f"- Score medio total crag: **{avg_scores['crag']:.2f}/20**",
        f"- Pontos de ranking acumulados (1o=3, 2o=2, 3o=1): baseline={rank_points['baseline']}, fusion={rank_points['fusion']}, crag={rank_points['crag']}",
        f'- Tempo medio por caso (pipeline completo): **{avg_elapsed:.2f}s**',
        '',
        '## Medias por criterio (0-5)',
        f"- Baseline: precisao={avg_dims['baseline']['precisao']}, cobertura={avg_dims['baseline']['cobertura']}, clareza={avg_dims['baseline']['clareza']}, aderencia={avg_dims['baseline']['aderencia_contexto']}",
        f"- Fusion: precisao={avg_dims['fusion']['precisao']}, cobertura={avg_dims['fusion']['cobertura']}, clareza={avg_dims['fusion']['clareza']}, aderencia={avg_dims['fusion']['aderencia_contexto']}",
        f"- CRAG: precisao={avg_dims['crag']['precisao']}, cobertura={avg_dims['crag']['cobertura']}, clareza={avg_dims['crag']['clareza']}, aderencia={avg_dims['crag']['aderencia_contexto']}",
        '',
        '## Resultado por colecao',
        '',
        '| Colecao | Baseline (/20) | Fusion (/20) | CRAG (/20) | Acao CRAG | Web chunks | Tempo(s) |',
        '|---|---:|---:|---:|---|---:|---:|',
    ]

    for r in results:
        lines.append(
            f"| `{r['collection']}` | {r['scores_total']['baseline']:.2f} | {r['scores_total']['fusion']:.2f} | {r['scores_total']['crag']:.2f} | {r['action_crag']} | {r['web_chunks']} | {r['elapsed_s']:.2f} |"
        )

    lines.append('')
    lines.append('## Comentarios curtos do juiz (amostra)')
    for r in results[:5]:
        if r['judge_comment']:
            lines.append(f"- `{r['collection']}`: {r['judge_comment']}")

    REPORT_MD.write_text('\n'.join(lines), encoding='utf-8')
    REPORT_JSON.write_text(
        json.dumps(
            {
                'avg_scores': avg_scores,
                'rank_points': rank_points,
                'avg_elapsed_s': avg_elapsed,
                'avg_dims': avg_dims,
                'results': results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )

    print(f'relatorios: {REPORT_MD} | {REPORT_JSON}')


if __name__ == '__main__':
    main()
