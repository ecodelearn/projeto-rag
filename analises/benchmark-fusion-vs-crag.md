# Benchmark: RAG-Fusion vs CRAG (rodada 1)

## Metodologia
- Fusion: 4 reformulacoes via LLM + consulta original, fusao por ranking reciproco (top-8).
- CRAG: busca local baseline (top-8) + avaliador LLM (CORRECT/AMBIGUOUS/INCORRECT).
- Para AMBIGUOUS/INCORRECT: busca web via DuckDuckGo e recomposicao de contexto.

## Resultado agregado
- Latencia media fusion: **9.27s**
- Latencia media CRAG: **7.67s**
- Overlap medio@8 (fusion vs crag): **0.78**
- Novelty media@8 do CRAG vs fusion: **0.22**
- Proporcao media de chunks web no CRAG: **0.11**
- Acoes do avaliador: CORRECT=7, AMBIGUOUS=2, INCORRECT=0

## Resultado por colecao

| Colecao | Fusion(s) | CRAG(s) | Acao | Web ratio | Overlap@8 | Novelty CRAG@8 |
|---|---:|---:|---|---:|---:|---:|
| `sandeco_prompts_v1` | 6.78 | 4.45 | CORRECT | 0.00 | 0.75 | 0.25 |
| `sandeco_guardrails_v1` | 9.20 | 9.35 | CORRECT | 0.00 | 0.50 | 0.50 |
| `sandeco_python_ia_v1` | 8.44 | 10.35 | CORRECT | 0.00 | 0.88 | 0.12 |
| `sandeco_crewai1_v1` | 10.96 | 7.11 | CORRECT | 0.00 | 0.88 | 0.12 |
| `sandeco_crewai2_v1` | 7.92 | 6.56 | CORRECT | 0.00 | 0.50 | 0.50 |
| `sandeco_mcp_a2a_v1` | 8.98 | 4.54 | CORRECT | 0.00 | 1.00 | 0.00 |
| `sandeco_rag_book_v1` | 10.59 | 12.63 | AMBIGUOUS | 0.50 | 0.75 | 0.25 |
| `sandeco_orange_v1` | 9.62 | 4.18 | CORRECT | 0.00 | 0.88 | 0.12 |
| `sandeco_deep_learning_v1` | 10.96 | 9.87 | AMBIGUOUS | 0.50 | 0.88 | 0.12 |

## Reformulacoes de exemplo (fusion)

### sandeco_prompts_v1
- Quais princípios práticos ajudam a criar prompts eficazes para tarefas técnicas?
- Quais diretrizes práticas promovem a produção de bons prompts para tarefas técnicas?
- Quais fundamentos práticos orientam a redação de prompts eficientes em tarefas técnicas?
- Quais práticas recomendadas devem guiar a construção de prompts de qualidade para tarefas técnicas?

### sandeco_guardrails_v1
- Como aplicar guardrails para reduzir respostas fora do objetivo em agentes que utilizam RAG?
- Quais guardrails podem ser usados para manter as respostas alinhadas ao objetivo em sistemas RAG?
- Como estabelecer guardrails para evitar desvios de objetivo em agentes com RAG?
- Quais estratégias de guardrails ajudam a limitar respostas que fogem do objetivo em agentes baseados em RAG?

### sandeco_python_ia_v1
- Como o Python facilita a construção de pipelines de IA para iniciantes?
- Qual função do Python em pipelines de IA voltados a iniciantes?
- Por que o Python é fundamental em pipelines de IA para quem está começando?
- De que forma o Python é utilizado em pipelines de IA para iniciantes?

### sandeco_crewai1_v1
- No CrewAI básico, como agentes, tarefas e equipes se conectam?
- No CrewAI básico, de que modo os agentes se conectam com as tarefas e as equipes?
- Como se relacionam agentes, tarefas e crews no CrewAI básico?
- Quais mecanismos unem agentes, tarefas e equipes no CrewAI na versão básica?

### sandeco_crewai2_v1
- Quais integrações práticas são mais comuns em automações com o CrewAI intermediário?
- No CrewAI intermediário, quais integrações práticas costumam ser mais utilizadas em automações?
- Quais são as integrações práticas mais frequentes em automações envolvendo o CrewAI intermediário?
- Quais integrações comuns aparecem com mais frequência em automações usando o CrewAI intermediário?

### sandeco_mcp_a2a_v1
- Quais são as diferenças entre MCP e A2A na arquitetura de agentes?
- Como MCP e A2A se comparam na arquitetura de agentes?
- O que diferencia MCP de A2A na arquitetura de agentes?
- Quais aspectos distinguem MCP de A2A na arquitetura de agentes?

### sandeco_rag_book_v1
- Quais são as diferenças entre o RAG clássico, o CRAG e o Agentic RAG?
- Como se diferenciam o RAG clássico, o CRAG e o Agentic RAG?
- Qual é a diferença entre RAG clássico, CRAG e Agentic RAG?
- Entre RAG clássico, CRAG e Agentic RAG, quais são as principais diferenças?

### sandeco_orange_v1
- Como o Orange Canvas facilita o aprendizado de IA visual e ciência de dados para iniciantes?
- Quais benefícios o Orange Canvas oferece a quem está começando em IA visual e ciência de dados?
- Quais recursos do Orange Canvas ajudam iniciantes em IA visual e ciência de dados a aprender de forma prática?
- Como iniciantes em IA visual e ciência de dados podem tirar proveito do Orange Canvas?

### sandeco_deep_learning_v1
- Quais são os fundamentos básicos de deep learning mais importantes para iniciar projetos?
- Quais conceitos centrais de deep learning devo dominar para começar um projeto?
- Quais pilares essenciais do deep learning são mais úteis no estágio inicial de um projeto?
- Quais conhecimentos fundamentais de deep learning são prioritários ao iniciar um projeto?