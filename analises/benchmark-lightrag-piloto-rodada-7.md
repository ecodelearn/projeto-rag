# Benchmark LightRAG Piloto - Rodada 7

- Colecao: `sandeco_rag_book_v1`
- Perguntas: 3
- Corpus piloto LightRAG: 80 chunks amostrados
- Indexacao: rebuilt

## Resultado agregado
- Score medio baseline: **16.67/20**
- Score medio LightRAG: **16.00/20**
- Latencia media baseline: **18.38s**
- Latencia media LightRAG: **37.58s**
- Vitorias: baseline=2, lightrag=1, draw=0

## Resultado por pergunta

| Pergunta | Baseline (/20) | LightRAG (/20) | Baseline(s) | LightRAG(s) |
|---|---:|---:|---:|---:|
| Qual a diferenca entre RAG classico, CRAG e Agentic RAG? | 10.00 | 19.00 | 21.14 | 13.51 |
| Como funciona a fase de indexacao no RAG e por que ela e importante? | 20.00 | 15.00 | 11.40 | 47.33 |
| Quando vale usar busca hibrida em vez de apenas busca vetorial? | 20.00 | 14.00 | 22.61 | 51.91 |