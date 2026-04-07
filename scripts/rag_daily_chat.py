from __future__ import annotations

import argparse
import hashlib
import html
import os
import re
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

ROOT = '/home/ecode/Documents/projetos/projeto-rag'
CHROMA_PATH = ROOT + '/sources/rag_memory/02 - RAG with memory/chroma_db'

COLLECTION_HINTS = {
    'sandeco_prompts_v1': 'prompt engineering, escrita de prompts, instrucoes para LLM',
    'sandeco_guardrails_v1': 'guardrails, seguranca, controle de agentes, politicas',
    'sandeco_python_ia_v1': 'python para IA, bibliotecas, scripts, automacao',
    'sandeco_crewai1_v1': 'CrewAI basico, agentes, tarefas, crews',
    'sandeco_crewai2_v1': 'CrewAI intermediario, integracoes, automacoes, APIs',
    'sandeco_mcp_a2a_v1': 'MCP, A2A, protocolos, arquitetura de agentes',
    'sandeco_rag_book_v1': 'RAG, retrieval, CRAG, agentic rag, fusion, hyde',
    'sandeco_orange_v1': 'Orange Canvas, IA visual, ciencia de dados no-code',
    'sandeco_deep_learning_v1': 'deep learning, redes neurais, fundamentos',
}


def _hash_text(s: str) -> str:
    return hashlib.sha1(s.encode('utf-8', errors='ignore')).hexdigest()


def search(chroma_client, emb_model, collection: str, query: str, n_results: int = 8):
    col = chroma_client.get_collection(collection)
    q_emb = emb_model.encode([query]).tolist()
    out = col.query(query_embeddings=q_emb, n_results=n_results, include=['documents'])
    return out['documents'][0]


def generate_rewrites(llm: OpenAI, model: str, question: str, n: int = 4) -> list[str]:
    prompt = (
        'Gere variacoes semanticas de consulta para busca RAG. '
        f'Crie {n} reformulacoes da pergunta abaixo, mantendo intencao. '
        'Responda somente com uma consulta por linha, sem numeracao.\n\n'
        f'Pergunta: {question}'
    )
    resp = llm.chat.completions.create(model=model, messages=[{'role': 'user', 'content': prompt}])
    txt = resp.choices[0].message.content or ''
    rewrites = [ln.strip('-• \t') for ln in txt.splitlines() if ln.strip()]
    return [r for r in rewrites if len(r) > 5][:n]


def fusion_chunks(chroma_client, emb_model, collection: str, question: str, rewrites: list[str], top_k: int = 8, per_query: int = 6):
    scores = {}
    docs_map = {}
    for q in [question] + rewrites:
        docs = search(chroma_client, emb_model, collection, q, n_results=per_query)
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


def eval_crag_action(llm: OpenAI, model: str, question: str, chunks: list[str]) -> str:
    contexto = '\n\n'.join(chunks[:8]) if chunks else '(sem chunks)'
    prompt = f"""Classifique se os chunks bastam para responder.
Responda APENAS: CORRECT, AMBIGUOUS ou INCORRECT.

Pergunta: {question}

Chunks:\n{contexto}
"""
    resp = llm.chat.completions.create(model=model, messages=[{'role': 'user', 'content': prompt}])
    raw = (resp.choices[0].message.content or '').upper()
    for t in ('CORRECT', 'AMBIGUOUS', 'INCORRECT'):
        if t in raw:
            return t
    return 'AMBIGUOUS'


def answer(llm: OpenAI, model: str, question: str, chunks: list[str]) -> str:
    ctx = '\n\n'.join(chunks[:8]) if chunks else '(sem contexto)'
    prompt = f"""Responda em pt-BR, markdown e de forma objetiva com base no contexto.
Se insuficiente, declare limites.

Pergunta:\n{question}\n\nContexto:\n{ctx}
"""
    resp = llm.chat.completions.create(model=model, messages=[{'role': 'user', 'content': prompt}])
    return (resp.choices[0].message.content or '').strip()


def route_collection(llm: OpenAI, model: str, question: str) -> str:
    choices = '\n'.join([f'- {k}: {v}' for k, v in COLLECTION_HINTS.items()])
    prompt = f"""Escolha a colecao mais adequada para responder a pergunta.
Retorne APENAS o nome da colecao.

Colecoes:\n{choices}

Pergunta: {question}
"""
    resp = llm.chat.completions.create(model=model, messages=[{'role': 'user', 'content': prompt}])
    txt = (resp.choices[0].message.content or '').strip()
    for c in COLLECTION_HINTS:
        if c in txt:
            return c
    return 'sandeco_rag_book_v1'


def main():
    parser = argparse.ArgumentParser(description='Chat diario do RAG Sandeco')
    parser.add_argument('--mode', choices=['baseline', 'fusion', 'crag'], default='baseline')
    parser.add_argument('--collection', default='auto', help='nome da colecao ou auto')
    parser.add_argument('--topk', type=int, default=8)
    args = parser.parse_args()

    load_dotenv(os.path.join(ROOT, '.env'))
    api_key = os.getenv('OPENAI_API_KEY')
    model = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
    if not api_key:
        raise SystemExit('OPENAI_API_KEY nao encontrado em /home/ecode/Documents/projetos/projeto-rag/.env')

    llm = OpenAI(api_key=api_key)
    chroma = chromadb.PersistentClient(path=CHROMA_PATH)
    emb = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    print(f'✅ RAG diario pronto | mode={args.mode} | collection={args.collection}')
    print('Digite sua pergunta (ou sair):')

    while True:
        q = input('> ').strip()
        if not q:
            continue
        if q.lower() in {'sair', 'exit', 'quit'}:
            break

        collection = args.collection
        if collection == 'auto':
            collection = route_collection(llm, model, q)

        base = search(chroma, emb, collection, q, n_results=args.topk)

        if args.mode == 'baseline':
            chunks = base
        elif args.mode == 'fusion':
            rw = generate_rewrites(llm, model, q, n=4)
            chunks = fusion_chunks(chroma, emb, collection, q, rw, top_k=args.topk, per_query=6)
        else:  # crag
            action = eval_crag_action(llm, model, q, base)
            if action == 'CORRECT':
                chunks = base
            elif action == 'AMBIGUOUS':
                chunks = (base + web_chunks_ddg(q, max_results=4))[:args.topk]
            else:
                chunks = web_chunks_ddg(q, max_results=8)[:args.topk]

        resp = answer(llm, model, q, chunks)
        print(f'\n[colecao={collection}]\n{resp}\n')


if __name__ == '__main__':
    main()
