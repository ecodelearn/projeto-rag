# Avaliacao qualitativa cega - rodada 6

## Metodo
- Tres metodos comparados por pergunta: baseline, fusion e crag.
- Para cada pergunta, respostas foram embaralhadas (A/B/C) antes da avaliacao.
- Juiz LLM aplicou rubrica 0-5 em: precisao, cobertura, clareza e aderencia ao contexto.

## Resultado agregado
- Score medio total baseline: **17.11/20**
- Score medio total fusion: **17.56/20**
- Score medio total crag: **16.11/20**
- Pontos de ranking acumulados (1o=3, 2o=2, 3o=1): baseline=20, fusion=21, crag=13
- Tempo medio por caso (pipeline completo): **102.20s**

## Medias por criterio (0-5)
- Baseline: precisao=4.22, cobertura=4.33, clareza=4.22, aderencia=4.33
- Fusion: precisao=4.22, cobertura=4.56, clareza=4.22, aderencia=4.56
- CRAG: precisao=4.0, cobertura=4.11, clareza=3.89, aderencia=4.11

## Resultado por colecao

| Colecao | Baseline (/20) | Fusion (/20) | CRAG (/20) | Acao CRAG | Web chunks | Tempo(s) |
|---|---:|---:|---:|---|---:|---:|
| `sandeco_prompts_v1` | 16.00 | 19.00 | 14.00 | CORRECT | 0 | 112.89 |
| `sandeco_guardrails_v1` | 20.00 | 17.00 | 12.00 | CORRECT | 0 | 91.83 |
| `sandeco_python_ia_v1` | 12.00 | 16.00 | 20.00 | CORRECT | 0 | 92.41 |
| `sandeco_crewai1_v1` | 16.00 | 20.00 | 16.00 | CORRECT | 0 | 112.21 |
| `sandeco_crewai2_v1` | 20.00 | 16.00 | 16.00 | CORRECT | 0 | 111.41 |
| `sandeco_mcp_a2a_v1` | 18.00 | 17.00 | 19.00 | CORRECT | 0 | 92.07 |
| `sandeco_rag_book_v1` | 17.00 | 16.00 | 16.00 | CORRECT | 0 | 138.82 |
| `sandeco_orange_v1` | 16.00 | 18.00 | 16.00 | CORRECT | 0 | 76.92 |
| `sandeco_deep_learning_v1` | 19.00 | 19.00 | 16.00 | CORRECT | 0 | 91.26 |

## Comentarios curtos do juiz (amostra)
- `sandeco_prompts_v1`: Avaliando objetivamente, a resposta B oferece a maior clareza, estrutura e cobertura de templates para prompts técnicos; A possui conteúdo útil porém menos estruturado e contém um erro pontual que afeta a precisão; C é sólido e bem definido, mas menos expansivo que B.
- `sandeco_guardrails_v1`: A oferece o conjunto mais completo de guardrails e fluxo iterativo, com prompts e métricas bem definidas. B é igualmente robusta e prática, mas um pouco menos detalhada que A. C é mais introdutório e requer maior definição de guardrails e fluxo para alinhar ao objetivo.
- `sandeco_python_ia_v1`: A oferece maior abrangência e exemplos práticos; B apresenta uma solução sólida com passos práticos; C é objetivo, porém menos detalhado. Todos estão alinhados ao contexto introdutório, com A sendo o mais completo.
- `sandeco_crewai1_v1`: Resposta B apresenta a visão mais completa, precisa e alinhada ao contexto, com definição clara de Agent, Task, Crew, e fluxo. A oferece bom passo a passo e exemplos; C é claro, mas menos abrangente.
- `sandeco_crewai2_v1`: A resposta B oferece a lista mais abrangente e bem alinhada ao ecossistema CrewAI intermediário, cobrindo APIs, bancos de dados, IA, mensageria, observabilidade, segurança e UI. A e C são sólidas, mas com cobertura e consistência levemente menores.