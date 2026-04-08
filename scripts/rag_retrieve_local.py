from __future__ import annotations

import argparse
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

ROOT = Path('/home/ecode/Documents/projetos/projeto-rag')
CHROMA_PATH = ROOT / 'sources' / 'rag_memory' / '02 - RAG with memory' / 'chroma_db'

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


def pick_collection(emb: SentenceTransformer, question: str, available: set[str]) -> str:
    candidates = [c for c in COLLECTION_HINTS if c in available]
    if not candidates:
        raise RuntimeError('Nenhuma colecao sandeco_*_v1 encontrada no ChromaDB')

    q_vec = emb.encode([question], normalize_embeddings=True)
    hints = [COLLECTION_HINTS[c] for c in candidates]
    h_vec = emb.encode(hints, normalize_embeddings=True)

    scores = (h_vec @ q_vec.T).reshape(-1)
    best_idx = int(scores.argmax())
    return candidates[best_idx]


def query_collection(client: chromadb.PersistentClient, emb: SentenceTransformer, collection: str, question: str, topk: int):
    col = client.get_collection(collection)
    q_emb = emb.encode([question]).tolist()
    out = col.query(
        query_embeddings=q_emb,
        n_results=max(1, min(topk, 20)),
        include=['documents', 'metadatas', 'distances'],
    )

    docs = out.get('documents', [[]])[0] or []
    ids = out.get('ids', [[]])[0] or []
    dists = out.get('distances', [[]])[0] or []
    metas = out.get('metadatas', [[]])[0] or []

    chunks = []
    for i, doc in enumerate(docs):
        chunks.append(
            {
                'collection': collection,
                'id': ids[i] if i < len(ids) else None,
                'distance': float(dists[i]) if i < len(dists) and dists[i] is not None else None,
                'metadata': metas[i] if i < len(metas) else None,
                'text': doc,
            }
        )
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description='Retrieval local do projeto-rag (sem LLM)')
    parser.add_argument('--question')
    parser.add_argument('--collection', default='auto', help='auto | all | nome da colecao')
    parser.add_argument('--topk', type=int, default=8)
    parser.add_argument('--list-collections', action='store_true')
    args = parser.parse_args()

    chroma = chromadb.PersistentClient(path=str(CHROMA_PATH))
    available = sorted([c.name for c in chroma.list_collections()])

    if args.list_collections:
        print(json.dumps({'collections': available}, ensure_ascii=False))
        return

    if not args.question:
        raise SystemExit('Passe --question ou use --list-collections')

    emb = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    available_set = set(available)

    if args.collection == 'auto':
        chosen = pick_collection(emb, args.question, available_set)
        chunks = query_collection(chroma, emb, chosen, args.question, args.topk)
        searched = [chosen]
        out_collection = chosen
    elif args.collection == 'all':
        searched = [c for c in available if c.startswith('sandeco_') and c.endswith('_v1')]
        if not searched:
            searched = [c for c in available if c.startswith('sandeco_')]
        if not searched:
            raise SystemExit('Nenhuma colecao sandeco_* encontrada para busca all')

        merged = []
        per_collection_topk = min(max(3, args.topk), 10)
        for c in searched:
            merged.extend(query_collection(chroma, emb, c, args.question, per_collection_topk))

        merged.sort(key=lambda x: float(x.get('distance') or 1e9))
        chunks = merged[: max(1, min(args.topk, 20))]
        out_collection = 'all'
    else:
        if args.collection not in available_set:
            raise SystemExit(f'Colecao nao encontrada: {args.collection}')
        chunks = query_collection(chroma, emb, args.collection, args.question, args.topk)
        searched = [args.collection]
        out_collection = args.collection

    print(
        json.dumps(
            {
                'collection': out_collection,
                'searched_collections': searched,
                'topk': args.topk,
                'chunks': chunks,
            },
            ensure_ascii=False,
        )
    )


if __name__ == '__main__':
    main()
