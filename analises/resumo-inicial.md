# Resumo inicial de análise

## Inventário técnico (alto nível)
- `rag_classico`: 9 arquivos `.py`, `requirements.txt` e `pyproject.toml`
- `rag_memory`: 10 arquivos `.py`, `requirements.txt` e `pyproject.toml`
- `agentic_rag`: 16 arquivos `.py`, `requirements.txt` e `pyproject.toml`
- `crag`: 11 arquivos `.py`, `requirements.txt` e `pyproject.toml`
- `adaptative_rag`: 33 arquivos `.py`, `pyproject.toml`
- `rag_fusion`: 10 arquivos `.py`, `pyproject.toml`
- `hyde_rag`: 10 arquivos `.py`, `pyproject.toml`

## Achados
- `hyde_rag` e `rag_fusion` são idênticos (mesma estrutura e hash de conteúdo).
- Todos vieram como ZIPs do Google Drive (não repositórios Git diretamente).

## Próxima análise sugerida
1. Levantar stack por projeto (frameworks, vector DB, provider LLM)
2. Criar matriz comparativa de capacidade:
   - ingestão
   - chunking
   - retriever (vetorial, híbrido, rerank)
   - memória
   - agente/roteamento
3. Escolher baseline de implementação para `projeto-rag`.
