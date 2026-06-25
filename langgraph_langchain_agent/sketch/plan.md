# plan.md — Enterprise DataOps Knowledge Hub
## W01: LlamaIndex + Pydantic | AIDE Brasil — Layer 2

---

## 1. VISÃO DO PROJETO

### O que estamos construindo
Um **Enterprise DataOps Knowledge Hub** — sistema RAG multi-fonte e conteinerizado que ingere dados estruturados (PostgreSQL), semi-estruturados (MongoDB) e não-estruturados (SeaweedFS/PDFs), indexa nos domínios **Ledger + Memory + Brain**, e os expõe via FastAPI + MCP como ferramenta consumível por AI Agents.

O objetivo final: um AI Agent (Claude Code) faz uma pergunta complexa cruzando os três domínios e recebe uma resposta sintetizada, com fontes, queries executadas e recomendação acionável.

### Arquitetura: 3 Domínios Cognitivos

```
Pergunta complexa do usuário
        │
        ▼
  ┌─────────────┐
  │ RouterEngine│  ← classifica, decompõe, orquestra
  └──────┬──────┘
         │ asyncio.gather (paralelo)
    ┌────┴────┬──────────┐
    ▼         ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│LEDGER  │ │MEMORY  │ │ BRAIN  │
│Postgres│ │ Qdrant │ │ Neo4j  │
│Text2SQL│ │Vector  │ │Cypher  │
│Search  │ │Search  │ │Traversal
└────────┘ └────────┘ └────────┘
    │         │          │
    └────┬────┴──────────┘
         ▼
  SynthesizedResponse (Pydantic)
         │
         ▼
  FastAPI /query
         │
         ▼
  MCP Server → Claude Code
```

| Domínio | Store | Retrieval | Pergunta típica |
|---------|-------|-----------|-----------------|
| **Ledger** | PostgreSQL | Text-to-SQL (`NLSQLTableQueryEngine`) | "Quantos clientes enterprise temos?" |
| **Memory** | Qdrant | Vector Search (`VectorStoreIndex`) | "Qual a política de retenção para PII?" |
| **Brain** | Neo4j | Graph Traversal (`KnowledgeGraphQueryEngine`) | "O que seria impactado se a tabela orders cair?" |

---

## 2. STACK TECNOLÓGICA

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| RAG Framework | LlamaIndex | >= 0.12 |
| Contratos | Pydantic | v2 |
| API | FastAPI + Uvicorn | >= 0.115 |
| Ledger | PostgreSQL | 16-alpine |
| Memory | Qdrant | latest |
| Brain | Neo4j | 5-community |
| Events | MongoDB | 7 |
| Data Lake | SeaweedFS | latest (S3-compat) |
| Embeddings | OpenAI text-embedding-3-small | — |
| LLM | OpenAI gpt-4.1-mini | — |
| Infra local | Docker Compose | v2 |
| Deploy | DigitalOcean Droplet | s-2vcpu-4gb |
| Agentic layer | MCP SDK (Python) | >= 1.0 |

> **Nota:** O projeto usa OpenAI como LLM padrão. Para usar Claude (Anthropic), substitua `llama-index-llms-openai` por `llama-index-llms-anthropic` e ajuste o `llm_model` em `EngineConfig`.

---

## 3. ESTRUTURA DE PASTAS

```
dataops-knowledge-hub/
│
├── CLAUDE.md                    ← contrato do agente
├── docker-compose.yml           ← infra local (dev)
├── docker-compose.production.yml← infra prod
├── Dockerfile                   ← build da app
├── pyproject.toml               ← dependências
├── Makefile                     ← comandos rápidos
├── .env.example                 ← template de variáveis
├── .gitignore
│
├── sketch/
│   ├── plan.md                  ← este arquivo
│   └── tasks.md                 ← lista de tarefas
│
├── docs/
│   └── w1-rag-content.md        ← material de referência
│
├── prompts/
│   ├── 1-build-claude-memory.md
│   ├── 2-build-scaffold.md
│   └── ...                      ← 14 prompts sequenciais
│
├── infra/
│   ├── scripts/
│   │   ├── init-databases.sql   ← DDL Postgres
│   │   ├── init-neo4j.cypher    ← seed do grafo
│   │   ├── init-seaweedfs.sh    ← cria bucket S3
│   │   └── seed-neo4j.sh        ← wrapper de execução
│   └── docs/                    ← docs que vão para o SeaweedFS
│       ├── data-retention-policy.md
│       ├── sla-definitions.md
│       ├── incident-response-runbook.md
│       └── data-dictionary.csv
│
├── generator/
│   ├── main.py                  ← loop contínuo de geração de dados
│   ├── Dockerfile
│   └── requirements.txt
│
├── src/
│   ├── __init__.py
│   │
│   ├── schemas/                 ← contratos Pydantic
│   │   ├── __init__.py
│   │   ├── domain.py            ← Customer, Order, PipelineEvent, etc.
│   │   ├── query.py             ← LedgerQueryResult, MemoryQueryResult, BrainQueryResult
│   │   └── api.py               ← QueryRequest, QueryResponse, HealthResponse
│   │
│   ├── ingestion/               ← pipeline LlamaIndex (só Memory)
│   │   ├── __init__.py
│   │   ├── config.py            ← IngestionConfig (pydantic-settings)
│   │   ├── readers.py           ← SeaweedFSReader, MongoDBReader
│   │   ├── pipeline.py          ← IngestionPipeline com LlamaIndex
│   │   └── run.py               ← entry point: python -m src.ingestion.run
│   │
│   ├── engines/                 ← query engines
│   │   ├── __init__.py
│   │   ├── config.py            ← EngineConfig (pydantic-settings)
│   │   ├── ledger.py            ← LedgerEngine (NLSQLTableQueryEngine)
│   │   ├── memory.py            ← MemoryEngine (VectorStoreIndex)
│   │   ├── brain.py             ← BrainEngine (Cypher/Graph)
│   │   └── router.py            ← RouterEngine (orquestra os 3)
│   │
│   ├── api/                     ← FastAPI
│   │   ├── __init__.py
│   │   ├── app.py               ← create_app() com lifespan
│   │   ├── main.py              ← uvicorn entry point
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── query.py         ← POST /api/v1/query
│   │       ├── health.py        ← GET /health
│   │       └── ingest.py        ← POST /api/v1/ingest (background task)
│   │
│   └── mcp/                     ← MCP Server
│       ├── __init__.py
│       ├── server.py            ← tools: query_knowledge_hub, check_platform_health, trigger_ingestion
│       └── run.py               ← entry point: python -m src.mcp.run
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_schemas.py
│   │   └── test_router_classification.py
│   └── integration/
│       ├── test_engines.py
│       ├── test_router.py
│       └── test_api.py
│
├── scripts/
│   ├── deploy-digitalocean.sh
│   ├── destroy-digitalocean.sh
│   └── deploy.sh
│
└── mcp-config.json              ← referência de config do MCP para Claude Code
```

---

## 4. MODELO DE DADOS

### PostgreSQL — Ledger

```sql
customers (id, name, email, plan[free|pro|enterprise], company, created_at)
products  (id, name, category, price, sku, active, created_at)
orders    (id, customer_id→customers, product_id→products, amount, quantity, status[pending|completed|failed|refunded], created_at)
```

### MongoDB — Events

```
event_logs    { pipeline_name, status, error_message, severity, duration_seconds, records_processed, timestamp }
user_activity { user_id, action, metadata, session_id, timestamp }
```

### Neo4j — Brain

**Nodes:** `Team`, `Pipeline`, `Table`, `Dashboard`

**Relationships:**
```
(Team)-[:OWNS]->(Pipeline)
(Team)-[:OWNS]->(Table)
(Pipeline)-[:READS_FROM]->(Table)
(Pipeline)-[:WRITES_TO]->(Table)
(Pipeline)-[:FEEDS]->(Pipeline)
(Table)-[:USED_BY]->(Dashboard)
```

**Seed data:** 3 Teams, 4 Pipelines, 5 Tables, 3 Dashboards

### SeaweedFS — Data Lake

Bucket: `dataops-lake`
```
/docs/data-retention-policy.md
/docs/sla-definitions.md
/docs/incident-response-runbook.md
/docs/data-dictionary.csv
/reports/daily-summary-YYYY-MM-DD.csv  ← gerados pelo Data Generator
```

---

## 5. PIPELINE RAG (9 STEPS)

### Fase de Ingestão (Offline — só para Memory/Qdrant)

```
SeaweedFS docs + MongoDB logs
        │
        ▼
SeaweedFSReader + MongoDBReader   [Step 1: Load]
        │
        ▼
SemanticSplitterNodeParser        [Step 2: Chunk]
        │
        ▼
TitleExtractor                    [Step 3: Metadata]
SummaryExtractor
KeywordExtractor (5 keywords)
QuestionsAnsweredExtractor (3 questions)
        │
        ▼
OpenAIEmbedding (text-embedding-3-small)  [Step 4: Embed]
        │
        ▼
QdrantVectorStore (collection: dataops-memory)  [Step 5: Index & Store]
```

> PostgreSQL e Neo4j **não passam por ingestão** — são consultados diretamente.

### Fase de Consulta (Runtime)

```
Pergunta do usuário               [Step 6: Query]
        │
        ▼
RouterEngine classifica           [Step 7: Route]
   + decompõe em sub-questions
        │
        ▼ asyncio.gather
[Ledger]  [Memory]  [Brain]       [Step 7: Retrieve]
  SQL     Vector     Cypher
        │
        ▼
LLM sintetiza todos os resultados [Step 8: Synthesize]
        │
        ▼
SynthesizedResponse (Pydantic)    [Step 9: Validate]
```

---

## 6. SCHEMAS PYDANTIC (CONTRATOS)

### Query Engines → Output

```python
# Ledger
LedgerQueryResult(sql_query_executed, summary, row_count, data_points)

# Memory
MemoryQueryResult(summary, sources, confidence[0-1], relevant_facts)

# Brain
BrainQueryResult(cypher_query_executed, summary, nodes_traversed, relationships_found, dependency_chain?)
```

### Router → Output

```python
SynthesizedResponse(answer, sub_questions, sources_consulted, confidence, recommendation?)
```

### API → Request/Response

```python
QueryRequest(question, sources?[ledger|memory|brain], include_metadata)
QueryResponse(question, answer, sub_questions, sources_consulted[SourceDetail], recommendation?, processing_time_ms, timestamp)
HealthResponse(status, services{postgres,qdrant,neo4j,mongo,seaweedfs}, uptime_seconds, version)
```

---

## 7. FASTAPI — ENDPOINTS

| Method | Path | Descrição |
|--------|------|-----------|
| `POST` | `/api/v1/query` | Query principal — aceita `QueryRequest`, retorna `QueryResponse` |
| `GET` | `/health` | Status de todos os serviços |
| `POST` | `/api/v1/ingest` | Trigger reingestion em background, retorna 202 com job_id |

**Lifespan:** `RouterEngine` inicializado uma vez no startup (caro — cria conexões).

---

## 8. MCP SERVER — TOOLS

| Tool | Descrição |
|------|-----------|
| `query_knowledge_hub` | Query cross-domain no Knowledge Hub |
| `check_platform_health` | Verifica status dos serviços |
| `trigger_ingestion` | Dispara re-ingestão dos documentos |

Transporte: `stdio` (para uso local com Claude Code)
`API_BASE_URL` configurável via env var (default: `http://localhost:8000`)

---

## 9. MAKEFILE — COMANDOS ESSENCIAIS

```makefile
make up              # docker compose up -d
make down            # docker compose down
make logs            # docker compose logs -f
make ingest          # python -m src.ingestion.run
make serve           # uvicorn src.api.main:app --reload
make query           # curl interativo para POST /api/v1/query
make test            # pytest tests/unit -v
make test-integration# pytest tests/integration -v --timeout=120
make test-all        # pytest tests/ -v --timeout=120
make deploy-do       # scripts/deploy-digitalocean.sh
make destroy-do      # scripts/destroy-digitalocean.sh
```

---

## 10. REGRAS DE ARQUITETURA (nunca viole)

1. **Todo output de LLM passa por Pydantic** — zero dicts soltos nas bordas do sistema.
2. **Ledger, Memory, Brain são engines independentes** — cada uma testável em isolamento.
3. **O RouterEngine orquestra, nunca acessa os stores diretamente** — separação de camadas.
4. **IngestionPipeline só para Memory** — PostgreSQL e Neo4j são consultados diretamente.
5. **Variáveis de ambiente via `.env`** — nenhuma credencial hardcoded.
6. **`async/await` em toda a aplicação** — FastAPI + LlamaIndex suportam async nativamente.
7. **Não use LangChain** — este projeto usa LlamaIndex exclusivamente.
8. **Não use ChromaDB** — use Qdrant.
9. **Não use in-memory vector stores em produção** — somente em testes.

---

## 11. DEPLOY — DigitalOcean

- **Instância:** `s-2vcpu-4gb` (~$24/mês), região `nyc1`
- **Image:** `docker-20-04` (Docker pré-instalado)
- **Deploy:** `make deploy-do` → `scripts/deploy-digitalocean.sh`
- **CI/CD:** git pull + rebuild na droplet via SSH
- **Teardown:** `make destroy-do`

**Após deploy:**
- API pública: `http://<DROPLET_IP>:8000`
- Docs: `http://<DROPLET_IP>:8000/docs`
- MCP produção: atualizar `API_BASE_URL` no `mcp-config.json`

---

## 12. O GRAND FINALE

```bash
# Claude Code conectado ao MCP Server em produção
claude

> Use the dataops-knowledge-hub tool to find out which customers are on the
  enterprise plan, what the SLA is for the billing pipeline, and what would
  happen if the orders table went down.
```

**O que acontece:**
1. Claude Code descobre a tool `query_knowledge_hub` via MCP
2. Chama a tool com a pergunta complexa
3. MCP Server faz POST para FastAPI em produção
4. RouterEngine classifica → 3 sub-questions em paralelo
5. Ledger (SQL) + Memory (vector) + Brain (Cypher) respondem
6. LLM sintetiza tudo em uma resposta coesa com fontes e recomendação
7. Claude Code exibe no terminal

**O AI Agent consome o sistema que ele mesmo construiu.**
