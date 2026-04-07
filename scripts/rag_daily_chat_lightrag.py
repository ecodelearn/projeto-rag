from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
from pathlib import Path

import chromadb
import numpy as np
from dotenv import load_dotenv
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.utils import EmbeddingFunc
from openai import OpenAI

ROOT = Path('/home/ecode/Documents/projetos/projeto-rag')
CHROMA_PATH = ROOT / 'sources' / 'rag_memory' / '02 - RAG with memory' / 'chroma_db'
WORKROOT = ROOT / 'frameworks' / 'lightrag_runs' / 'sandeco_rag_daily'

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


def get_collection_docs(collection: str, limit: int = 120):
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    col = client.get_collection(collection)
    data = col.get(include=['documents'])
    docs = data.get('documents', []) or []
    rnd = random.Random(42)
    rnd.shuffle(docs)
    return docs[:limit]


async def make_embedding_func(model_name: str = 'text-embedding-3-small', max_token: int = 8192):
    async def _embed(texts: list[str]) -> np.ndarray:
        return await openai_embed.func(texts, model=model_name)

    test = await _embed(['teste'])
    dim = int(test.shape[1])
    return EmbeddingFunc(embedding_dim=dim, max_token_size=max_token, func=_embed)


async def init_rag(workdir: Path, llm_model_name: str):
    workdir.mkdir(parents=True, exist_ok=True)
    emb_func = await make_embedding_func()
    rag = LightRAG(
        working_dir=str(workdir),
        embedding_func=emb_func,
        llm_model_func=gpt_4o_mini_complete,
        llm_model_name=llm_model_name,
        log_level='INFO',
    )
    await rag.initialize_storages()
    return rag


def ensure_index(rag: LightRAG, workdir: Path, docs: list[str]):
    marker = workdir / '.indexed.json'
    sig = _hash_text(''.join(sorted(_hash_text(d) for d in docs)))

    if marker.exists():
        try:
            payload = json.loads(marker.read_text(encoding='utf-8'))
            if payload.get('sig') == sig:
                return 'reused'
        except Exception:
            pass

    for d in docs:
        rag.insert(d)

    marker.write_text(json.dumps({'sig': sig, 'docs': len(docs)}), encoding='utf-8')
    return 'rebuilt'


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
    parser = argparse.ArgumentParser(description='Chat diário com LightRAG (sem Neo4j)')
    parser.add_argument('--collection', default='auto', help='nome da colecao ou auto')
    parser.add_argument('--mode', choices=['naive', 'local', 'global', 'hybrid'], default='hybrid')
    parser.add_argument('--sample', type=int, default=120, help='quantidade de chunks para index piloto')
    parser.add_argument('--skip-index', action='store_true', help='nao reindexar corpus')
    args = parser.parse_args()

    load_dotenv(ROOT / '.env')
    api_key = os.getenv('OPENAI_API_KEY')
    model = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
    if not api_key:
        raise SystemExit('OPENAI_API_KEY nao encontrado em /home/ecode/Documents/projetos/projeto-rag/.env')
    os.environ['OPENAI_API_KEY'] = api_key

    llm = OpenAI(api_key=api_key)

    rag_cache: dict[str, LightRAG] = {}

    print(f'✅ LightRAG pronto | collection={args.collection} | mode={args.mode}')
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

        if collection not in rag_cache:
            workdir = WORKROOT / collection
            rag = asyncio.run(init_rag(workdir, model))
            if args.skip_index:
                status = 'skipped'
            else:
                docs = get_collection_docs(collection, limit=args.sample)
                status = ensure_index(rag, workdir, docs)
            rag_cache[collection] = rag
            print(f'🔧 Colecao carregada: {collection} | index={status}')

        rag = rag_cache[collection]
        resp = rag.query(q, param=QueryParam(mode=args.mode))
        print(f'\n[colecao={collection}]\n{str(resp).strip()}\n')


if __name__ == '__main__':
    main()
