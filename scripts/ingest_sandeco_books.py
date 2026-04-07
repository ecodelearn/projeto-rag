from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path

ROOT = Path('/home/ecode/Documents/projetos/projeto-rag')
VAULT = Path('/home/ecode/Documents/projetos/obsidian/obsidian-vault')
RAW = VAULT / '10 Fontes Brutas' / 'PDFs'
SRC = ROOT / 'sources' / 'rag_memory' / '02 - RAG with memory'
REPORT = ROOT / 'analises' / 'ingestao-lote-livros-sandeco.md'

BOOKS = [
    {
        'book': 'Prompts em Acao Vol. 1',
        'pdf': RAW / 'PROMPST-SANDECO' / 'Prompts em Ação - Engenharia de Prompts Para Leigos - Sandeco Macedo-1.pdf',
        'collection': 'sandeco_prompts_v1',
    },
    {
        'book': 'Guardrails (Prompts Vol. 2)',
        'pdf': RAW / 'GUARDRAILS-SANDECO' / 'Branco_Prompts_em_Ação_vol_2__guardrails.pdf',
        'collection': 'sandeco_guardrails_v1',
    },
    {
        'book': 'Python para Inteligencia Artificial',
        'pdf': RAW / 'PYTHON-SANDECO' / 'Python para Inteligência Artificial v4 Br.pdf',
        'collection': 'sandeco_python_ia_v1',
    },
    {
        'book': 'CrewAI Vol. 1 (Basico)',
        'pdf': RAW / 'CREWAI-1-SANDECO' / '01___CrewAI_Livro_Básico - Branco.pdf',
        'collection': 'sandeco_crewai1_v1',
    },
    {
        'book': 'CrewAI Vol. 2 (Intermediario)',
        'pdf': RAW / 'CREWAI-2-SADECO' / 'CREWAI 2 VERSÃO FINAL.pdf',
        'collection': 'sandeco_crewai2_v1',
    },
    {
        'book': 'MCP e A2A',
        'pdf': RAW / 'MCP-E-A2A-SANDECO' / 'MCP_Livro - Versão Final.pdf',
        'collection': 'sandeco_mcp_a2a_v1',
    },
    {
        'book': 'RAG',
        'pdf': RAW / 'RAG-SANDECO' / 'RAG Versão Final - branca.pdf',
        'collection': 'sandeco_rag_book_v1',
    },
    {
        'book': 'Orange Canvas',
        'pdf': RAW / 'ORANGE-CANVAS-SANDECO' / 'LIVRO v7 Final - INTELIGÊNCIA ARTIFICIAL VISUAL COM ORANGE CANVAS - SANDECO MACEDO - BRANCO.pdf',
        'collection': 'sandeco_orange_v1',
    },
    {
        'book': 'Deep Learning (bonus)',
        'pdf': RAW / 'DEEP-LEARNING-SANDECO' / 'Livro_Intensivo_de_Deep_Learning-1.pdf',
        'collection': 'sandeco_deep_learning_v1',
    },
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    import sys

    if not SRC.exists():
        raise SystemExit(f'fonte nao encontrada: {SRC}')

    sys.path.insert(0, str(SRC))
    from semantic_encoder import SemanticEncoder  # noqa

    os.chdir(SRC)

    tmp_docs = SRC / 'docs_ingest_tmp'
    markdown_dir = SRC / 'markdown'

    results = []
    errors = []
    seen_hashes: dict[str, str] = {}

    for item in BOOKS:
        book = item['book']
        pdf = item['pdf']
        collection = item['collection']

        if not pdf.exists():
            errors.append(f'[faltando] {book}: {pdf}')
            continue

        digest = sha256_file(pdf)
        if digest in seen_hashes:
            results.append({
                'book': book,
                'collection': collection,
                'pdf': str(pdf),
                'status': f'duplicado de {seen_hashes[digest]}',
                'chunks': 0,
                'seconds': 0,
                'sha256': digest,
            })
            continue

        seen_hashes[digest] = book

        # isolamento por ingestao (evita mistura de markdown legado)
        if tmp_docs.exists():
            shutil.rmtree(tmp_docs)
        tmp_docs.mkdir(parents=True, exist_ok=True)

        if markdown_dir.exists():
            shutil.rmtree(markdown_dir)

        # copia para nome simples sem acento/espaco para reduzir chance de erro de parser
        staged_pdf = tmp_docs / 'book.pdf'
        shutil.copy2(pdf, staged_pdf)

        t0 = time.time()
        try:
            enc = SemanticEncoder(docs_dir=str(tmp_docs), chunk_size=1800, overlap_size=250)
            stats = enc.build(reset_collection=True, collection_name=collection)
            dt = round(time.time() - t0, 2)
            results.append({
                'book': book,
                'collection': collection,
                'pdf': str(pdf),
                'status': 'ok',
                'chunks': int(stats.get('chunks_salvos', 0)),
                'seconds': dt,
                'sha256': digest,
            })
        except Exception as e:  # noqa
            dt = round(time.time() - t0, 2)
            errors.append(f'[erro] {book}: {e}')
            results.append({
                'book': book,
                'collection': collection,
                'pdf': str(pdf),
                'status': f'erro: {e}',
                'chunks': 0,
                'seconds': dt,
                'sha256': digest,
            })

    total_chunks = sum(r['chunks'] for r in results if r['status'] == 'ok')

    lines = [
        '# Ingestao em lote - livros do Sandeco',
        '',
        f'- Total de livros planejados: {len(BOOKS)}',
        f'- Ingestoes OK: {sum(1 for r in results if r["status"] == "ok")}',
        f'- Total de chunks gerados: {total_chunks}',
        '',
        '## Resultado por livro',
        '',
        '| Livro | Colecao | Chunks | Tempo(s) | Status |',
        '|---|---|---:|---:|---|',
    ]

    for r in results:
        lines.append(f"| {r['book']} | `{r['collection']}` | {r['chunks']} | {r['seconds']} | {r['status']} |")

    lines += ['', '## Fontes usadas', '']
    for r in results:
        lines.append(f"- `{r['book']}` -> `{r['pdf']}`")

    if errors:
        lines += ['', '## Erros', '']
        lines.extend([f'- {e}' for e in errors])

    REPORT.write_text('\n'.join(lines), encoding='utf-8')

    (ROOT / 'analises' / 'ingestao-lote-livros-sandeco.json').write_text(
        json.dumps({'results': results, 'errors': errors}, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    print(f'relatorio: {REPORT}')


if __name__ == '__main__':
    main()
