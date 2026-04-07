# Configuração OpenAI (gpt-5-nano) com streaming

## Objetivo
Executar o baseline `rag_memory` usando OpenAI com saída em streaming.

## Ajustes locais aplicados no baseline
No diretório `sources/rag_memory/02 - RAG with memory`:
- `generation.py`
  - suporte a provider por ambiente (`LLM_PROVIDER=openai|gemini`)
  - suporte a modelo por ambiente (`OPENAI_MODEL`, default `gpt-5-nano`)
  - suporte a streaming para OpenAI (`generate_stream`)
  - fallback de chaves: `OPENAI_API_KEY`, `OPENAI_KEY`, `OPENAI_TOKEN`
- `main.py`
  - execução com streaming token a token no terminal
  - configuração por ambiente de coleção e talk id

## Variáveis recomendadas (.env)
```env
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-5-nano
OPENAI_API_KEY=...
RAG_COLLECTION=synthetic_dataset_papers
TALK_ID=sandeco-chat-001
```

## Execução
```bash
cd "/home/ecode/Documents/projetos/projeto-rag/sources/rag_memory/02 - RAG with memory"
source .venv/bin/activate
python main.py
```

## Observações
- O diretório `sources/` é ignorado no Git por política de privacidade/licença.
- Sempre registrar em `analises/` qualquer patch local aplicado aos pacotes de terceiros.
