# Rodada 2 - Ingestao do livro de RAG (Sandeco)

## Objetivo
Ingerir o livro de RAG no baseline `rag_memory` e validar uma consulta ponta a ponta com OpenAI.

## Fonte usada
- Arquivo local: `10 Fontes Brutas/PDFs/RAG Versão Final - branca.pdf`
- Copiado para: `sources/rag_memory/02 - RAG with memory/docs_sandeco_rag/`

## Pipeline executado
1. Instalacao de dependencias de PDF do MarkItDown (`markitdown[all]`)
2. Build da colecao vetorial com `SemanticEncoder`
3. Consulta com Retriever + Augmentation + Generation (OpenAI)

## Resultado
- Colecao criada: `sandeco_rag_book_v1`
- Chunks salvos: `942`
- Validacao de consulta: OK
- Pergunta de teste: "O que e RAG e qual a diferenca entre RAG classico e Agentic RAG?"
- Resposta gerada com sucesso via `gpt-5-nano`

## Observacoes tecnicas
- O `semantic_encoder.py` retorna `colecao: documentos_rag` no dict de stats (bug de atributo interno), mas a colecao real criada foi `sandeco_rag_book_v1`.
- Confirmacao feita listando colecoes do ChromaDB.
