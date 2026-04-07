from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import re
import statistics
import time
from pathlib import Path

import chromadb
import numpy as np
from dotenv import load_dotenv
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.utils import EmbeddingFunc
from openai import OpenAI
from sentence_transformers import SentenceTransformer

ROOT = Path('/home/ecode/Documents/projetos/projeto-rag')
CHROMA_PATH = ROOT / 'sources' / 'rag_memory' / '02 - RAG with memory' / 'chroma_db'
WORKDIR = ROOT / 'frameworks' / 'lightrag_runs' / 'sandeco_rag_pilot'
REPORT_MD = ROOT / 'analises' / 'benchmark-lightrag-piloto-rodada-7.md'
REPORT_JSON = ROOT / 'analises' / 'benchmark-lightrag-piloto-rodada-7.json'

COLLECTION = 'sandeco_rag_book_v1'
QUESTIONS = [
    'Qual a diferenca entre RAG classico, CRAG e Agentic RAG?',
    'Como funciona a fase de indexacao no RAG e por que ela e importante?',
    'Quando vale usar busca hibrida em vez de apenas busca vetorial?',
]


async def make_embedding_func(model_name: str = 'text-embedding-3-small', max_token: int = 8192):
    async def _embed(texts: list[str]) -> np.ndarray:
        return await openai_embed.func(texts, model=model_name)

    test = await _embed(['teste'])
    dim = int(test.shape[1])
    return EmbeddingFunc(embedding_dim=dim, max_token_size=max_token, func=_embed)


async def init_lightrag(llm_model_name: str):
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


def _hash_text(s: str) -> str:
    return hashlib.sha1(s.encode('utf-8', errors='ignore')).hexdigest()


def get_collection_docs(limit: int = 80):
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    col = client.get_collection(COLLECTION)
    data = col.get(include=['documents'])
    docs = data.get('documents', []) or []
    # amostra deterministica para piloto
    rnd = random.Random(42)
    rnd.shuffle(docs)
    return docs[:limit]


def ensure_lightrag_indexed(rag: LightRAG, docs: list[str]):
    marker = WORKDIR / '.indexed.json'
    current_sig = _hash_text(''.join(sorted(_hash_text(d) for d in docs)))

    if marker.exists():
        try:
            payload = json.loads(marker.read_text(encoding='utf-8'))
            if payload.get('sig') == current_sig:
                return 'reused'
        except Exception:
            pass

    # limpa indice simples do piloto
    for p in WORKDIR.glob('*'):
        if p.name.startswith('.'):
            continue
        if p.is_file():
            p.unlink(missing_ok=True)

    for d in docs:
        rag.insert(d)

    marker.write_text(json.dumps({'sig': current_sig, 'docs': len(docs)}, ensure_ascii=False), encoding='utf-8')
    return 'rebuilt'


def baseline_answer(llm: OpenAI, llm_model: str, emb_model: SentenceTransformer, question: str):
    t0 = time.time()
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    col = client.get_collection(COLLECTION)
    q_emb = emb_model.encode([question]).tolist()
    out = col.query(query_embeddings=q_emb, n_results=8, include=['documents'])
    chunks = out['documents'][0]
    ctx = '\n\n'.join(chunks)
    prompt = f"""Responda em pt-BR e markdown usando o contexto abaixo.
Se o contexto for insuficiente, explicite limites.

Pergunta:
{question}

Contexto:
{ctx}
"""
    resp = llm.chat.completions.create(model=llm_model, messages=[{'role': 'user', 'content': prompt}])
    ans = (resp.choices[0].message.content or '').strip()
    return ans, time.time() - t0


def lightrag_answer(rag: LightRAG, question: str):
    t0 = time.time()
    ans = rag.query(question, param=QueryParam(mode='hybrid'))
    return str(ans).strip(), time.time() - t0


def parse_json(text: str):
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if not m:
        return {}
    raw = m.group(0)
    try:
        return json.loads(raw)
    except Exception:
        return {}


def judge_pair(llm: OpenAI, llm_model: str, question: str, a: str, b: str):
    prompt = f"""Compare as duas respostas sem saber o metodo.
Pergunta: {question}

[A]
{a}

[B]
{b}

Avalie (0-5): precisao, cobertura, clareza, aderencia_contexto.
Retorne APENAS JSON:
{{
  "A": {{"precisao":0,"cobertura":0,"clareza":0,"aderencia_contexto":0}},
  "B": {{"precisao":0,"cobertura":0,"clareza":0,"aderencia_contexto":0}},
  "winner": "A|B|draw",
  "comentario": "..."
}}
"""
    resp = llm.chat.completions.create(model=llm_model, messages=[{'role': 'user', 'content': prompt}])
    return parse_json(resp.choices[0].message.content or '{}')


def score_total(d: dict):
    return float(d.get('precisao', 0)) + float(d.get('cobertura', 0)) + float(d.get('clareza', 0)) + float(d.get('aderencia_contexto', 0))


def main():
    load_dotenv(ROOT / '.env')
    api_key = os.getenv('OPENAI_API_KEY')
    llm_model = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
    if not api_key:
        raise SystemExit('OPENAI_API_KEY nao encontrado')

    os.environ['OPENAI_API_KEY'] = api_key

    llm = OpenAI(api_key=api_key)
    emb = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    rag = asyncio.run(init_lightrag(llm_model_name=llm_model))
    docs = get_collection_docs(limit=80)
    index_status = ensure_lightrag_indexed(rag, docs)

    rows = []
    baseline_scores, lightrag_scores = [], []
    baseline_lat, lightrag_lat = [], []
    win = {'baseline': 0, 'lightrag': 0, 'draw': 0}

    for q in QUESTIONS:
        base_ans, base_t = baseline_answer(llm, llm_model, emb, q)
        lg_ans, lg_t = lightrag_answer(rag, q)

        # cegamento simples
        if random.random() < 0.5:
            judged = judge_pair(llm, llm_model, q, base_ans, lg_ans)
            a_map, b_map = 'baseline', 'lightrag'
        else:
            judged = judge_pair(llm, llm_model, q, lg_ans, base_ans)
            a_map, b_map = 'lightrag', 'baseline'

        sa = score_total(judged.get('A', {}))
        sb = score_total(judged.get('B', {}))

        scores = {'baseline': 0.0, 'lightrag': 0.0}
        scores[a_map] = sa
        scores[b_map] = sb

        baseline_scores.append(scores['baseline'])
        lightrag_scores.append(scores['lightrag'])
        baseline_lat.append(base_t)
        lightrag_lat.append(lg_t)

        w = (judged.get('winner', 'draw') or 'draw').lower()
        if w == 'a':
            win[a_map] += 1
        elif w == 'b':
            win[b_map] += 1
        else:
            win['draw'] += 1

        rows.append(
            {
                'question': q,
                'baseline_score': round(scores['baseline'], 2),
                'lightrag_score': round(scores['lightrag'], 2),
                'baseline_s': round(base_t, 2),
                'lightrag_s': round(lg_t, 2),
                'winner': judged.get('winner', 'draw'),
                'comentario': judged.get('comentario', ''),
            }
        )

    avg_base_score = statistics.mean(baseline_scores) if baseline_scores else 0.0
    avg_lg_score = statistics.mean(lightrag_scores) if lightrag_scores else 0.0
    avg_base_lat = statistics.mean(baseline_lat) if baseline_lat else 0.0
    avg_lg_lat = statistics.mean(lightrag_lat) if lightrag_lat else 0.0

    lines = [
        '# Benchmark LightRAG Piloto - Rodada 7',
        '',
        f'- Colecao: `{COLLECTION}`',
        f'- Perguntas: {len(QUESTIONS)}',
        f'- Corpus piloto LightRAG: {len(docs)} chunks amostrados',
        f'- Indexacao: {index_status}',
        '',
        '## Resultado agregado',
        f'- Score medio baseline: **{avg_base_score:.2f}/20**',
        f'- Score medio LightRAG: **{avg_lg_score:.2f}/20**',
        f'- Latencia media baseline: **{avg_base_lat:.2f}s**',
        f'- Latencia media LightRAG: **{avg_lg_lat:.2f}s**',
        f"- Vitorias: baseline={win['baseline']}, lightrag={win['lightrag']}, draw={win['draw']}",
        '',
        '## Resultado por pergunta',
        '',
        '| Pergunta | Baseline (/20) | LightRAG (/20) | Baseline(s) | LightRAG(s) |',
        '|---|---:|---:|---:|---:|',
    ]
    for r in rows:
        lines.append(
            f"| {r['question']} | {r['baseline_score']:.2f} | {r['lightrag_score']:.2f} | {r['baseline_s']:.2f} | {r['lightrag_s']:.2f} |"
        )

    REPORT_MD.write_text('\n'.join(lines), encoding='utf-8')
    REPORT_JSON.write_text(
        json.dumps(
            {
                'collection': COLLECTION,
                'questions': QUESTIONS,
                'docs_sampled': len(docs),
                'index_status': index_status,
                'avg': {
                    'baseline_score': round(avg_base_score, 2),
                    'lightrag_score': round(avg_lg_score, 2),
                    'baseline_s': round(avg_base_lat, 2),
                    'lightrag_s': round(avg_lg_lat, 2),
                },
                'wins': win,
                'rows': rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )
    print(f'relatorios: {REPORT_MD} | {REPORT_JSON}')


if __name__ == '__main__':
    main()
