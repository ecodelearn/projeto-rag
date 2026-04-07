# Material base para artigo (RAG Sandeco)

## Titulo de trabalho (provisorio)
"RAG em Base Autoral Multi-Colecao: Trade-offs entre Baseline, RAG-Fusion e CRAG"

## Problema
Como equilibrar cobertura semantica e latencia em uma base de conhecimento autoral composta por livros tecnicos (trilha Sandeco)?

## Setup experimental
- Base: 9 livros ingeridos em colecoes dedicadas (`sandeco_*_v1`), total de 2480 chunks.
- Embedding: `paraphrase-multilingual-MiniLM-L12-v2`.
- Vetorstore: ChromaDB.
- LLM de apoio: `gpt-5-nano`.

## Resultados-chave (ate agora)
1. Baseline vs Fusion
   - Baseline: ~0.03s
   - Fusion: ~9.37s
   - Novelty@8 do Fusion: ~0.19
   - Leitura: Fusion amplia cobertura, mas com custo alto de latencia.

2. Fusion vs CRAG
   - Fusion: ~9.27s
   - CRAG: ~7.67s
   - Novelty@8 do CRAG vs Fusion: ~0.22
   - Acoes CRAG: CORRECT=7, AMBIGUOUS=2, INCORRECT=0
   - Uso medio de web chunks no CRAG: ~0.11
   - Leitura: CRAG foi mais eficiente em latencia media nesta rodada e trouxe contexto novo de forma seletiva.

## Hipotese para discussao
- Fusion e melhor para aumentar recall de forma sistematica.
- CRAG e melhor como camada corretiva seletiva, especialmente quando a base local e parcialmente suficiente.
- Politica hibrida pode reduzir custo: baseline -> fusion (quando necessario) -> CRAG (quando ambiguo/incorreto).

## Estrutura sugerida do artigo
1. Introducao e motivacao
2. Base de conhecimento e desenho experimental
3. Metodologia (baseline, fusion, crag)
4. Resultados quantitativos
5. Discussao de trade-offs e estrategia de orquestracao
6. Limitacoes e trabalhos futuros

## Proximos experimentos para fortalecer artigo
- Avaliacao qualitativa cega da resposta final (nao apenas retrieval)
- Testes com perguntas fora de distribuicao
- Curva custo x qualidade com top-k e numero de reformulacoes
- Comparacao com roteamento agentico multi-colecao
