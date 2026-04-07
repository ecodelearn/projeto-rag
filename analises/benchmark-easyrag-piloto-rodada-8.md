# Benchmark EasyRAG Piloto - Rodada 8

## Tipo de rodada
- Rodada de viabilidade tecnica e prontidao de execucao local (framework externo).

- Status: **pilot_blocked**

## Checagens
- Repo clonado: True
- GPU detectada: False (NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver. Make sure that the latest NVIDIA driver is installed and running.)
- requirements.txt: True (118 dependencias listadas)
- Config com GLM: True
- Chaves placeholder no config: True
- Smoke de dependencias: `{'llama_index': False, 'qdrant_client': False, 'rank_bm25': False, 'jieba': False}`

## Bloqueadores
- Sem GPU dedicada detectada para o perfil recomendado do EasyRAG (>=16GB).
- Config padrao do EasyRAG depende de chaves GLM (llm_keys com placeholder).
- Pipeline de referencia do EasyRAG esta acoplado a GLM-4 no config padrao.

## Recomendacao de proximo passo
- Executar piloto funcional em ambiente com GPU e stack dedicada para EasyRAG.
- Adaptar config para provider OpenAI (ou provider local equivalente), mantendo mesma suite de perguntas da pesquisa.
- So comparar com rodadas anteriores apos paridade minima de setup (corpus, perguntas, criterio de avaliacao).