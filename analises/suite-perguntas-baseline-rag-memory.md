# Suite de perguntas - baseline `rag_memory`

## Objetivo
Conjunto inicial para validar retrieval, consistência e comportamento do pipeline antes da ingestão dos livros.

## Perguntas (rodada 1)
1. O que é um synthetic dataset?
2. Quais são vantagens de usar dados sintéticos em visão computacional?
3. Quais são os riscos de viés em datasets sintéticos?
4. Como avaliar qualidade de um dataset sintético?
5. Qual a diferença entre dados reais e sintéticos em treinamento de modelos?
6. Quais técnicas podem ser usadas para gerar dados sintéticos?
7. Em quais cenários drones se beneficiam de datasets sintéticos?
8. O que é domain shift e como isso afeta modelos treinados com dados sintéticos?
9. Quais métricas são usadas para avaliar detecção de objetos em datasets de drones?
10. Em que situações usar dados sintéticos pode ser inadequado?

## Critérios de avaliação
- Relevância dos chunks recuperados (top-k)
- Cobertura da pergunta (suficiente/insuficiente)
- Repetição de chunks entre perguntas
- Latência média de retrieval
