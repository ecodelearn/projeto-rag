from pathlib import Path
import time
import sys

SRC = Path('/home/ecode/Documents/projetos/projeto-rag/sources/rag_memory/02 - RAG with memory')
if not SRC.exists():
    raise SystemExit(f'fonte nao encontrada: {SRC}')

sys.path.insert(0, str(SRC))
from retriever import Retriever  # noqa

queries = [
    'O que e um synthetic dataset?',
    'Quais sao vantagens de usar dados sinteticos em visao computacional?',
    'Quais sao os riscos de vies em datasets sinteticos?',
    'Como avaliar qualidade de um dataset sintetico?',
    'Qual a diferenca entre dados reais e sinteticos em treinamento de modelos?',
]

retriever = Retriever(collection_name='synthetic_dataset_papers')

out = []
for q in queries:
    t0 = time.time()
    chunks = retriever.search(q, n_results=3) or []
    dt = time.time() - t0
    out.append((q, dt, chunks))

report = Path('/home/ecode/Documents/projetos/projeto-rag/analises/benchmark-retrieval-rag-memory.md')
lines = ['# Benchmark de retrieval - rag_memory (rodada 1)', '']

for i, (q, dt, chunks) in enumerate(out, 1):
    lines.append(f'## Q{i}. {q}')
    lines.append(f'- Latencia: {dt:.2f}s')
    lines.append(f'- Chunks retornados: {len(chunks)}')
    for j, c in enumerate(chunks, 1):
        snippet = ' '.join(c.split())[:260]
        lines.append(f'  - [{j}] {snippet}...')
    lines.append('')

avg = sum(x[1] for x in out) / len(out)
lines.append(f'**Latencia media:** {avg:.2f}s')

report.write_text('\n'.join(lines), encoding='utf-8')
print(f'relatorio gerado: {report}')
