# projeto-rag

> Laboratorio pratico de RAG para uso real: ingestao de base autoral, benchmark comparativo e operacao diaria.

## Visao geral
Este repositorio consolida um ciclo completo de engenharia de RAG:
- ingestao de conhecimento em colecoes vetoriais dedicadas,
- comparacao tecnica entre estrategias de retrieval,
- avaliacao qualitativa cega das respostas,
- preparo de material para publicacao tecnica (artigo).

## Objetivo
Construir uma base de conhecimento **solida, auditavel e reutilizavel** para IA aplicada, com foco em:
- qualidade de resposta,
- latencia operacional,
- robustez em perguntas ambiguas,
- continuidade de evolucao (baseline -> fusion -> crag -> agentic).

## Resultados ja obtidos

![Resumo visual de qualidade e latencia](assets/benchmark_overview.png)

### Base de conhecimento
- 9 colecoes vetoriais dedicadas (`sandeco_*_v1`)
- 2480 chunks ingeridos

### Benchmarks
- **Rodada 4 — Baseline vs Fusion**
  - baseline: ~0.03s
  - fusion: ~9.37s
  - novelty@8 do fusion: ~0.19

- **Rodada 5 — Fusion vs CRAG**
  - fusion: ~9.27s
  - crag: ~7.67s
  - novelty@8 do crag vs fusion: ~0.22

- **Rodada 6 — Avaliacao qualitativa cega**
  - baseline: 18.33/20
  - fusion: 17.78/20
  - crag: 18.72/20

## Uso diario (chat RAG)
Script operacional:
- `scripts/rag_daily_chat.py`

Exemplos:
```bash
cd "/home/ecode/Documents/projetos/projeto-rag/sources/rag_memory/02 - RAG with memory"
source .venv/bin/activate

# Modo rapido (padrao recomendado)
python /home/ecode/Documents/projetos/projeto-rag/scripts/rag_daily_chat.py --mode baseline --collection auto

# Modo expansao semantica
python /home/ecode/Documents/projetos/projeto-rag/scripts/rag_daily_chat.py --mode fusion --collection auto

# Modo corretivo
python /home/ecode/Documents/projetos/projeto-rag/scripts/rag_daily_chat.py --mode crag --collection auto
```

## Estrutura do repositorio
- `scripts/`: automacoes de ingestao, benchmark e operacao
- `analises/`: resultados, comparativos e rascunho de artigo
- `downloads/`: artefatos brutos locais (**ignorado no git**)
- `sources/`: codigo extraido/local de terceiros (**ignorado no git**)

## Arquivos-chave
- `analises/ingestao-lote-livros-sandeco.md`
- `analises/benchmark-baseline-vs-fusion.md`
- `analises/benchmark-fusion-vs-crag.md`
- `analises/avaliacao-qualitativa-cega-rodada-6.md`
- `analises/artigo-rascunho-rag-v1.md`
- `analises/material-artigo-rag.md`

## Seguranca e privacidade
Este projeto segue politica explicita de versionamento:
- **Nao publicar** PDFs/livros, fontes brutas e artefatos protegidos.
- **Nao publicar** `.env`, tokens e credenciais.
- Publicar apenas codigo proprio, scripts e resultados analiticos.

## Proximos passos
- rodada de validacao com frameworks externos (LightRAG, EasyRAG, RAG-Anything)
- desenho de orquestracao adaptativa de producao
- consolidacao final do artigo tecnico

---
Se este projeto te ajudou, abra uma issue com sugestoes de experimento ou benchmark adicional.
