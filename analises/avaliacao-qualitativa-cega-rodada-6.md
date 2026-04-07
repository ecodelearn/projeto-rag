# Avaliacao qualitativa cega - rodada 6

## Metodo
- Tres metodos comparados por pergunta: baseline, fusion e crag.
- Para cada pergunta, respostas foram embaralhadas (A/B/C) antes da avaliacao.
- Juiz LLM aplicou rubrica 0-5 em: precisao, cobertura, clareza e aderencia ao contexto.

## Resultado agregado
- Score medio total baseline: **18.33/20**
- Score medio total fusion: **17.78/20**
- Score medio total crag: **18.72/20**
- Pontos de ranking acumulados (1o=3, 2o=2, 3o=1): baseline=15, fusion=18, crag=21
- Tempo medio por caso (pipeline completo): **96.71s**

## Resultado por colecao

| Colecao | Baseline (/20) | Fusion (/20) | CRAG (/20) | Acao CRAG | Web chunks | Tempo(s) |
|---|---:|---:|---:|---|---:|---:|
| `sandeco_prompts_v1` | 18.00 | 16.00 | 19.50 | CORRECT | 0 | 116.98 |
| `sandeco_guardrails_v1` | 19.00 | 12.00 | 17.00 | CORRECT | 0 | 85.54 |
| `sandeco_python_ia_v1` | 17.00 | 20.00 | 20.00 | CORRECT | 0 | 107.64 |
| `sandeco_crewai1_v1` | 18.00 | 20.00 | 18.00 | CORRECT | 0 | 98.01 |
| `sandeco_crewai2_v1` | 17.00 | 19.00 | 20.00 | CORRECT | 0 | 84.97 |
| `sandeco_mcp_a2a_v1` | 18.00 | 18.00 | 18.00 | CORRECT | 0 | 83.58 |
| `sandeco_rag_book_v1` | 20.00 | 18.00 | 16.00 | CORRECT | 0 | 108.39 |
| `sandeco_orange_v1` | 19.00 | 19.00 | 20.00 | CORRECT | 0 | 71.38 |
| `sandeco_deep_learning_v1` | 19.00 | 18.00 | 20.00 | CORRECT | 0 | 113.88 |

## Comentarios curtos do juiz (amostra)
- `sandeco_prompts_v1`: A oferece a avaliação mais completa e estruturada, incluindo templates e exemplos; C é sólido e útil, mas menos abrangente que A; B é bom, porém menos alinhado ao formato JSON exigido.
- `sandeco_guardrails_v1`: A oferece o conjunto mais completo de guardrails e critérios; C apresenta uma versão prática, clara e direta; B é menos focal e menos detalhado sobre guardrails.
- `sandeco_python_ia_v1`: A oferece o panorama mais completo com exemplo de código e fluxo end-to-end; B reforça o pipeline, integração e deploy com boa clareza; C apresenta uma visão sólida porém menos detalhada que A/B.
- `sandeco_crewai1_v1`: Resposta B oferece a explicação mais completa e prática, incluindo fluxo, paralelização e hierarquia. C é sólido e claro, cobrindo o essencial com exemplos, enquanto A está correto, mas menos abrangente em comparação com B e C.
- `sandeco_crewai2_v1`: A é o mais detalhado e alinhado com o ecossistema CrewAI (Tools, @tool, Streamlit). C é estruturado e abrangente, com foco em governança e IA. B é direto e conciso, mas menos cobertivo.