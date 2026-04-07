# Rascunho de Artigo — RAG em Base Autoral Multi-Colecao

## Titulo (provisorio)
**RAG em Base Autoral Multi-Colecao: trade-offs entre Baseline, RAG-Fusion e CRAG em uma trilha tecnica de IA aplicada**

## Resumo
Este trabalho investiga o comportamento de diferentes estrategias de Retrieval-Augmented Generation (RAG) sobre uma base autoral composta por livros tecnicos de IA aplicada. A base foi organizada em 9 colecoes vetoriais dedicadas, totalizando 2480 chunks. Comparamos tres abordagens: baseline vetorial, RAG-Fusion e CRAG. Os resultados mostram um trade-off claro entre cobertura semantica, latencia e qualidade final percebida. O RAG-Fusion aumenta diversidade de contexto, porem com maior custo temporal. O CRAG, quando usado de forma seletiva, apresentou boa relacao entre qualidade e custo em comparacao ao Fusion. Propomos uma estrategia de orquestracao progressiva para uso diario: baseline -> fusion (quando necessario) -> crag (quando ambiguo/incorreto).

## 1. Introducao
Sistemas RAG em contexto real precisam equilibrar tres fatores: (i) qualidade da resposta, (ii) latencia e (iii) robustez frente a perguntas ambíguas. Em bases autorais com conhecimento denso e especializado, uma unica estrategia de retrieval pode nao ser suficiente em todos os cenarios. Este estudo avalia empiricamente, em um ambiente controlado, como baseline, Fusion e CRAG se comportam sobre uma trilha completa de livros tecnicos.

## 2. Base de conhecimento e setup experimental
### 2.1 Corpus
- 9 livros tecnicos da trilha Sandeco
- 9 colecoes no ChromaDB (`sandeco_*_v1`)
- 2480 chunks no total

### 2.2 Stack
- Vetorstore: ChromaDB
- Embeddings: `paraphrase-multilingual-MiniLM-L12-v2`
- LLM de apoio: `gpt-5-nano`
- Pipeline base: ingestao + retrieval + geracao

### 2.3 Metodologia
Foram realizadas tres rodadas principais:
1. Baseline vs Fusion (quantitativo de retrieval)
2. Fusion vs CRAG (quantitativo de retrieval + corretivo)
3. Avaliacao qualitativa cega (qualidade final de respostas)

## 3. Resultados
### 3.1 Baseline vs Fusion (Rodada 4)
- Latencia media baseline: **0.03s**
- Latencia media fusion: **9.37s**
- Novelty media@8 (novos chunks no fusion): **0.19**
- Overlap medio@8: **0.79**

**Leitura:** Fusion ampliou cobertura de contexto, mas com custo alto de latencia.

### 3.2 Fusion vs CRAG (Rodada 5)
- Latencia media fusion: **9.27s**
- Latencia media CRAG: **7.67s**
- Novelty media@8 do CRAG vs Fusion: **0.22**
- Uso medio de chunks web no CRAG: **0.11**
- Acoes CRAG: CORRECT=7, AMBIGUOUS=2, INCORRECT=0

**Leitura:** CRAG atuou de forma seletiva e apresentou melhor custo medio temporal nesta rodada.

### 3.3 Avaliacao qualitativa cega (Rodada 6)
- Score medio total baseline: **18.33/20**
- Score medio total fusion: **17.78/20**
- Score medio total CRAG: **18.72/20**
- Ranking acumulado: baseline=15, fusion=18, crag=21

**Leitura:** qualidade alta em todos os metodos, com leve vantagem do CRAG no conjunto avaliado.

## 4. Discussao
Os resultados sugerem que:
- Baseline e muito eficiente para consultas diretas e de baixa ambiguidade.
- Fusion e util para ampliar cobertura semantica, principalmente em perguntas abertas.
- CRAG e efetivo como camada corretiva, sobretudo quando a base local e parcialmente suficiente.

Isso favorece uma arquitetura adaptativa por politicas:
1. Tentar baseline primeiro.
2. Acionar fusion em caso de baixa cobertura percebida.
3. Acionar crag quando o avaliador indicar ambiguidade ou insuficiencia.

## 5. Ameacas a validade
- Julgamento qualitativo realizado por LLM (mesmo com cegamento A/B/C).
- Uma pergunta por colecao nas rodadas quantitativas iniciais.
- Ausencia de avaliacao humana independente nesta versao.

## 6. Conclusao
A estrategia multi-metodo mostrou-se promissora para bases autorais tecnicas. Em nosso ambiente, CRAG e baseline apresentaram melhor equilibrio de qualidade e custo que Fusion isoladamente, enquanto Fusion manteve valor para aumentar diversidade de contexto. O proximo passo e consolidar um orquestrador de uso diario com politica adaptativa e avaliacao humana complementar.

## 7. Trabalhos futuros
- Avaliacao humana dupla-cega
- Curva de custo x qualidade por top-k e numero de reformulacoes
- Integracao de roteamento agentico multi-colecao
- Benchmark com frameworks externos (LightRAG, EasyRAG, RAG-Anything)

## Referencias internas (artefatos)
- `analises/benchmark-baseline-vs-fusion.md`
- `analises/benchmark-fusion-vs-crag.md`
- `analises/avaliacao-qualitativa-cega-rodada-6.md`
- `analises/material-artigo-rag.md`
