# Plano de validacao de frameworks externos (LightRAG, EasyRAG, RAG-Anything)

## Pergunta
Vale testar frameworks fora da metodologia atual (professor)?

## Resposta curta
Sim, compensa — mas em fase controlada, mantendo a stack atual como baseline oficial.

## Por que compensa
- Aumenta robustez metodologica do artigo (comparacao externa real).
- Evita lock-in em uma implementacao unica.
- Permite avaliar ganhos de grafo/multimodalidade com evidencias.

## Riscos
- Desvio de foco e atraso operacional.
- Aumento de complexidade de infraestrutura.
- Comparacoes injustas sem padronizacao de dataset/perguntas.

## Estrategia recomendada
1. Congelar baseline atual como referencia oficial (`baseline`, `fusion`, `crag`).
2. Definir harness de avaliacao unico (mesmas perguntas, mesmas metricas).
3. Testar frameworks em ordem de risco:
   - LightRAG (menor risco, foco grafo)
   - EasyRAG (menor friccao de integracao)
   - RAG-Anything (mais complexo, fase posterior)
4. Publicar resultado como comparativo incremental, nao substituicao imediata.

## Criterios de decisao
- Qualidade (score qualitativo cego)
- Latencia media
- Custo por pergunta
- Complexidade de operacao
- Esforco de manutencao

## Criterio de adocao
- So adotar como stack principal se superar baseline atual em pelo menos 2 eixos sem degradar criticamente os demais.
