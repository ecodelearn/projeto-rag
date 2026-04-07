# Matriz comparativa de baselines RAG (rodada 1)

## Escopo
Análise estática inicial dos projetos baixados pelos links do livro de RAG do Sandeco.

## Projetos avaliados
- `rag_classico`
- `rag_memory`
- `agentic_rag`
- `crag`
- `adaptative_rag`
- `rag_fusion`
- `hyde_rag`

## Achados rápidos
- `hyde_rag` e `rag_fusion` vieram com o mesmo conteúdo (duplicados).
- Todos usam Python com base em ChromaDB.
- Há evolução progressiva por camadas: clássico -> memória -> agentic -> corretivo/híbrido/grafo.

## Matriz (alto nível)
| Projeto | Capacidade central | Dependências-chave | Infra extra | Complexidade | Uso recomendado agora |
|---|---|---|---|---|---|
| rag_classico | Ingestão + busca vetorial + geração | chromadb, sentence-transformers, google-genai | Não | Baixa | Base didática e sanity check |
| rag_memory | RAG clássico + memória de conversa | + redis | Redis (docker-compose) | Baixa/Média | **Baseline inicial recomendado** |
| agentic_rag | Roteamento de dataset por agente | + crewai | LLM para roteador | Média | Fase 2 (após baseline estável) |
| crag | Avaliação de chunks + correção via web | busca externa DuckDuckGo + evaluator | Internet | Média | Fase 2/3 para robustez factual |
| rag_fusion | Expansão de consulta (multi-query) | geração de queries + retriever | Não | Média | Fase 2 para recall |
| hyde_rag | (pacote recebido idêntico ao rag_fusion) | idem rag_fusion | Não | Média | Não usar separado nesta rodada |
| adaptative_rag | Classificador de query + vectorRAG + graphRAG (Neo4j) | chromadb, google-genai, módulos de grafo | Neo4j + plugins + streamlit | Alta | Fase 3 (arquitetura avançada) |

## Recomendação de sequência
1. `rag_memory` como baseline operacional
2. `rag_fusion` para melhorar recuperação (recall)
3. `crag` para correção de contexto quando recuperação falhar
4. `agentic_rag` para roteamento entre coleções
5. `adaptative_rag` para camada híbrida com grafo

## Critérios para decidir baseline final (rodada 2)
- Qualidade de resposta com citação de fonte
- Consistência entre perguntas parecidas
- Facilidade de operar localmente
- Custo/latência
- Facilidade de manutenção

## Riscos observados
- Repositórios vieram em ZIP e com artefatos locais já inclusos (`.env`, `chroma_db`, `__pycache__`, `.git` interno).
- Dependências divergentes entre `requirements.txt` e `pyproject.toml` em alguns projetos.
- Sem README preenchido nos pacotes extraídos (vários `README.md` vazios).
