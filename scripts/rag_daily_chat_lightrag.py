from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import random
from pathlib import Path

import chromadb
import numpy as np
from dotenv import load_dotenv
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.utils import EmbeddingFunc

ROOT = Path('/home/ecode/Documents/projetos/projeto-rag')
CHROMA_PATH = ROOT / 'sources' / 'rag_memory' / '02 - RAG with memory' / 'chroma_db'
WORKDIR = ROOT / 'frameworks' / 'lightrag_runs' / 'sandeco_rag_daily'


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


async def init_rag(llm_model_name: str):
    WORKDIR.mkdir(parents=True, exist_ok=True)
    emb_func = await make_embedding_func()
    rag = LightRAG(
        working_dir=str(WORKDIR),
        embedding_func=emb_func,
        llm_model_func=gpt_4o_mini_complete,
        llm_model_name=llm_model_name,
        log_level='INFO',
    )
    await rag.initialize_storages()
    return rag


def ensure_index(rag: LightRAG, docs: list[str]):
    marker = WORKDIR / '.indexed.json'
    sig = _hash_text(''.join(sorted(_hash_text(d) for d in docs)))

    if marker.exists():
        try:
            import json

            payload = json.loads(marker.read_text(encoding='utf-8'))
            if payload.get('sig') == sig:
                return 'reused'
        except Exception:
            pass

    for d in docs:
        rag.insert(d)

    marker.write_text(f'{{"sig":"{sig}","docs":{len(docs)}}}', encoding='utf-8')
    return 'rebuilt'


def main():
    parser = argparse.ArgumentParser(description='Chat diário com LightRAG (sem Neo4j)')
    parser.add_argument('--collection', default='sandeco_rag_book_v1')
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

    rag = asyncio.run(init_rag(model))

    if args.skip_index:
        status = 'skipped'
    else:
        docs = get_collection_docs(args.collection, limit=args.sample)
        status = ensure_index(rag, docs)

    print(f'✅ LightRAG pronto | collection={args.collection} | mode={args.mode} | index={status}')
    print('Digite sua pergunta (ou sair):')

    while True:
        q = input('> ').strip()
        if not q:
            continue
        if q.lower() in {'sair', 'exit', 'quit'}:
            break

        resp = rag.query(q, param=QueryParam(mode=args.mode))
        print('\n' + str(resp).strip() + '\n')


if __name__ == '__main__':
    main()
