# Benchmark: Baseline vs RAG-Fusion (rodada 1)

## Metodologia
- Baseline: 1 consulta por pergunta, top-8 no Chroma.
- Fusion: 4 reformulacoes (LLM) + consulta original, fusao por Reciprocal Rank, top-8 final.
- Embeddings: paraphrase-multilingual-MiniLM-L12-v2.

## Resultado agregado
- Latencia media baseline: **0.03s**
- Latencia media fusion: **9.37s**
- Overlap medio@8 (baseline vs fusion): **0.79**
- Novelty media@8 (novos chunks no fusion): **0.19**
- Distancia media baseline (menor melhor): **10.3629**
- Distancia media fusion (menor melhor): **10.6313**

## Resultado por colecao

| Colecao | Baseline(s) | Fusion(s) | Overlap@8 | Novelty@8 | Dist baseline | Dist fusion |
|---|---:|---:|---:|---:|---:|---:|
| `sandeco_prompts_v1` | 0.03 | 10.72 | 0.75 | 0.25 | 8.5122 | 8.4473 |
| `sandeco_guardrails_v1` | 0.03 | 9.29 | 0.62 | 0.38 | 7.3297 | 7.1043 |
| `sandeco_python_ia_v1` | 0.03 | 6.46 | 0.88 | 0.12 | 12.1786 | 13.3424 |
| `sandeco_crewai1_v1` | 0.03 | 8.07 | 1.00 | 0.00 | 9.8132 | 10.1520 |
| `sandeco_crewai2_v1` | 0.03 | 9.24 | 0.50 | 0.50 | 7.3587 | 8.6862 |
| `sandeco_mcp_a2a_v1` | 0.03 | 12.90 | 0.88 | 0.12 | 12.7463 | 12.6486 |
| `sandeco_rag_book_v1` | 0.04 | 13.06 | 0.75 | 0.25 | 16.3520 | 15.3902 |
| `sandeco_orange_v1` | 0.04 | 8.33 | 0.88 | 0.12 | 9.5426 | 9.6217 |
| `sandeco_deep_learning_v1` | 0.02 | 6.22 | 0.88 | 0.00 | 9.4331 | 10.2890 |

## Reformulacoes usadas (amostra)

### sandeco_prompts_v1
- Quais diretrizes práticas ajudam a formular prompts eficazes para tarefas técnicas?
- Quais princípios pragmáticos orientam a criação de prompts de alta qualidade para atividades técnicas?
- Quais boas práticas devem ser seguidas ao escrever prompts para tarefas técnicas?
- Quais fundamentos úteis contribuem para construir prompts eficientes voltados a tarefas técnicas?

### sandeco_guardrails_v1
- Quais guardrails aplicar para reduzir respostas fora do objetivo em agentes de IA com RAG
- Como implementar guardrails para manter as respostas dos agentes no objetivo em sistemas baseados em RAG de busca
- Quais estratégias de guardrails ajudam a evitar respostas não alinhadas em agentes que utilizam recuperação de informações (RAG)
- Como configurar controles de guardrails para minimizar respostas irrelevantes em agentes de IA com recuperação de conhecimento (RAG)

### sandeco_python_ia_v1
- Qual é o papel do Python em pipelines de IA para iniciantes?
- Como o Python é utilizado em pipelines de IA para iniciantes?
- Por que o Python é importante em pipelines de IA para iniciantes?
- De que forma o Python contribui para pipelines de IA para iniciantes?

### sandeco_crewai1_v1
- No CrewAI básico, como agentes, tarefas e crews se conectam?
- No CrewAI básico, qual é o mecanismo de ligação entre agentes, tarefas e crews?
- No CrewAI básico, como agentes, tarefas e crews se relacionam entre si?
- No CrewAI básico, de que maneira agentes, tarefas e crews se conectam?

### sandeco_crewai2_v1
- Quais integrações práticas são mais comuns em automações no CrewAI intermediário?
- Quais integrações práticas costumam ser as mais usadas em automações na camada intermediária do CrewAI?
- Quais tipos de integração são mais frequentes em automações dentro do CrewAI intermediário?
- Quais integrações comuns, na prática, são usadas em automações no CrewAI intermediário?

### sandeco_mcp_a2a_v1
- Quais são as diferenças entre MCP e A2A na arquitetura de agentes?
- Como MCP difere de A2A na arquitetura de agentes?
- Quais são as distinções entre MCP e A2A dentro da arquitetura de agentes?
- Na arquitetura de agentes, o que diferencia MCP de A2A?

### sandeco_rag_book_v1
- Quais são as diferenças entre RAG clássico, CRAG e Agentic RAG?
- Como se distinguem o RAG clássico, o CRAG e o Agentic RAG?
- Quais são as diferenças-chave entre RAG clássico, CRAG e Agentic RAG?
- RAG clássico, CRAG e Agentic RAG: em que se diferenciam?

### sandeco_orange_v1
- Como o Orange Canvas auxilia iniciantes em IA visual e ciência de dados?
- Quais recursos do Orange Canvas ajudam quem está começando em IA visual e ciência de dados?
- De que modo o Orange Canvas facilita o aprendizado de IA visual e ciência de dados para iniciantes?
- Quais benefícios o Orange Canvas oferece a iniciantes em IA visual e ciência de dados?

### sandeco_deep_learning_v1
- Quais são os fundamentos de deep learning mais importantes para começar um projeto?
- Quais pilares do deep learning são essenciais para quem está iniciando um projeto?
- Quais conhecimentos básicos de deep learning são recomendados para começar um projeto?
- Quais conceitos-chave de deep learning devem ser aprendidos primeiro ao iniciar um projeto?