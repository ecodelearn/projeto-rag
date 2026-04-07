# Diagnostico tecnico - baseline `rag_memory`

## Contexto
Avaliação do pacote extraído em `sources/rag_memory/02 - RAG with memory` para uso como baseline do projeto.

## Achados

### 1) Import quebrado em `augmentation.py`
- Arquivo importa `from memory_rag import MemoryRAG`.
- Não existe `memory_rag.py` no pacote.
- Existe `memory.py` com classe `Memory` compatível no comportamento esperado.

Impacto:
- Execução falha logo no import.

Ação proposta:
- Criar shim local `memory_rag.py` com alias para `Memory`.

### 2) Dependência de Redis para memória
- `memory.py` conecta em `redis://localhost:6379`.
- Há `docker-compose.yml` no pacote para subir Redis.

Impacto:
- Sem Redis ativo, fluxo com memória não sobe.

Ação proposta:
- Subir Redis via Docker Compose antes da execução.

### 3) Chave de API Gemini
- `generation.py` usa `google-genai`.
- Precisamos de chave em ambiente (`GEMINI_API_KEY`) e compatibilidade com `GOOGLE_API_KEY`.

Impacto:
- Sem chave, chamada de geração falha.

Ação proposta:
- Exportar ambas variáveis no shell de execução.

### 4) Base vetorial prévia
- `main.py` pressupõe coleção já criada no ChromaDB.
- Pipeline exige indexação prévia (`semantic_encoder`/script de build).

Impacto:
- Chat sem indexação não retorna coleção.

Ação proposta:
- Rodar fase de build antes do chat interativo.

## Decisão operacional
- Baseline `rag_memory` segue válido para começar.
- Vamos usar uma camada de bootstrap local para corrigir lacunas do pacote sem alterar princípios do projeto.
