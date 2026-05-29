# tasks.md — Enterprise DataOps Knowledge Hub
## Build Checklist | Execute em ordem sequencial

**Legenda:** `[ ]` todo · `[~]` in progress · `[x]` done

Referências: `sketch/plan.md` (arquitetura) · `prompts/` (prompts detalhados)

---

## FASE 0 — CONTRATO E SCAFFOLD

### Task 00 — Criar CLAUDE.md
**Prompt:** `prompts/1-build-claude-memory.md`

```
[ ] Criar CLAUDE.md na raiz do projeto com:
    [ ] Seção 1: Project Overview (Ledger + Memory + Brain)
    [ ] Seção 2: Tech Stack com versões
    [ ] Seção 3: Architecture Rules (Pydantic em todo output LLM, sem LangChain, sem ChromaDB)
    [ ] Seção 4: Code Standards (Python 3.11+, async/await, type hints, pyproject.toml)
    [ ] Seção 5: Project Structure (referência ao sketch/plan.md)
    [ ] Seção 6: Naming Conventions (snake_case, PascalCase, kebab-case)
    [ ] Seção 7: Testing (pytest + pytest-asyncio, end-to-end obrigatório)
    [ ] Seção 8: References (sketch/plan.md, docs/)
    [ ] Seção 9: Workflow (ler prompts/ em ordem, confirmar antes de avançar)
    [ ] Seção 10: Constraints (não LangChain, não ChromaDB, não in-memory prod)
```

**Validação:**
- [ ] Todas as 10 seções presentes
- [ ] Referencia `sketch/plan.md` e `docs/`
- [ ] Workflow menciona a pasta `prompts/`

---

### Task 01 — Scaffold do Projeto
**Prompt:** `prompts/2-build-scaffold.md`

```
[ ] Criar estrutura de diretórios completa:
    [ ] infra/scripts/.gitkeep
    [ ] infra/docs/.gitkeep (placeholder — docs viram na Task 03)
    [ ] generator/.gitkeep
    [ ] src/__init__.py
    [ ] src/schemas/__init__.py
    [ ] src/ingestion/__init__.py
    [ ] src/engines/__init__.py
    [ ] src/api/__init__.py
    [ ] src/api/routes/__init__.py
    [ ] src/mcp/__init__.py
    [ ] tests/__init__.py
    [ ] scripts/.gitkeep

[ ] Criar arquivos base:
    [ ] .env.example (todas as variáveis: OPENAI_API_KEY, POSTGRES_*, MONGO_*, QDRANT_*, NEO4J_*, SEAWEEDFS_*)
    [ ] .gitignore (Python, .env, IDE, Docker override, data files)
    [ ] pyproject.toml (todas as dependências com versões: llama-index>=0.12, pydantic>=2.0, fastapi>=0.115, sqlalchemy>=2.0, psycopg2-binary, pymongo, qdrant-client>=1.12, neo4j>=5.25, boto3, faker, python-dotenv, httpx, mcp>=1.0)
    [ ] Makefile (up, down, logs, restart, status, ingest, serve, query, test, test-integration, test-all)
    [ ] README.md (overview, arquitetura, quick start)
```

**Validação:**
- [ ] `find src -name "*.py" | sort` mostra todos os `__init__.py`
- [ ] `.env.example` tem todas as variáveis
- [ ] `pyproject.toml` lista todas as dependências com versões mínimas

---

## FASE 1 — INFRAESTRUTURA

### Task 02 — Docker Compose
**Prompt:** `prompts/3-build-docker-compose.md`

```
[ ] Criar docker-compose.yml com os 5 serviços:
    [ ] postgres:16-alpine (porta 5432, volume pg_data, healthcheck pg_isready, mount init-databases.sql)
    [ ] mongo:7 (porta 27017, volume mongo_data, healthcheck mongosh ping)
    [ ] qdrant/qdrant:latest (portas 6333/6334, volume qdrant_data, healthcheck /healthz)
    [ ] neo4j:5-community (portas 7474/7687, volume neo4j_data, NEO4J_AUTH, APOC plugin, healthcheck cypher-shell)
    [ ] chrislusf/seaweedfs (portas 8333/9333, volume seaweedfs_data, healthcheck /cluster/status)

[ ] Network: dataops-network (bridge)
[ ] Named volumes: pg_data, mongo_data, qdrant_data, neo4j_data, seaweedfs_data
[ ] env_file: .env para postgres e neo4j
```

**Validação:**
- [ ] `docker compose config` sem erros
- [ ] `docker compose up -d` → todos os serviços sobem
- [ ] `docker compose ps` → todos "healthy" em 60s
- [ ] `curl http://localhost:6333/healthz` → ok
- [ ] `curl http://localhost:9333/cluster/status` → JSON

---

### Task 03 — Init Scripts
**Prompt:** `prompts/4-build-init-scripts.md`

```
[ ] infra/scripts/init-databases.sql:
    [ ] CREATE TABLE customers (id, name, email, plan, company, created_at)
    [ ] CREATE TABLE products (id, name, category, price, sku, active, created_at)
    [ ] CREATE TABLE orders (id, customer_id, product_id, amount, quantity, status, created_at)
    [ ] Indexes: orders(customer_id), orders(status), orders(created_at), customers(plan), products(category)

[ ] infra/scripts/init-neo4j.cypher:
    [ ] Constraints de unicidade (Pipeline.name, Table.name, Dashboard.name, Team.name)
    [ ] Seed: 3 Teams (team-billing, team-analytics, team-platform)
    [ ] Seed: 5 Tables (customers, orders, products, fact_revenue, dim_customers)
    [ ] Seed: 4 Pipelines (etl_billing_daily, etl_orders_hourly, etl_customer_sync, analytics_revenue_agg)
    [ ] Seed: 3 Dashboards (Revenue Overview, Customer Health, Pipeline Monitor)
    [ ] Relacionamentos: OWNS, READS_FROM, WRITES_TO, FEEDS, USED_BY

[ ] infra/scripts/init-seaweedfs.sh:
    [ ] Aguarda SeaweedFS ficar healthy
    [ ] Cria bucket dataops-lake via S3 API (aws --endpoint-url)

[ ] infra/scripts/seed-neo4j.sh:
    [ ] Aguarda Neo4j ficar healthy
    [ ] Executa init-neo4j.cypher via cypher-shell

[ ] infra/docs/ — Documentos seed para o SeaweedFS:
    [ ] data-retention-policy.md (PII: 90 dias, transacional: 7 anos, logs: 30 dias, LGPD)
    [ ] sla-definitions.md (SLA por pipeline: uptime %, latência máxima, escalation)
    [ ] incident-response-runbook.md (P1-P4, canais, rollback, post-mortem)
    [ ] data-dictionary.csv (table, column, type, description, owner, pii_flag, sla)

[ ] Atualizar docker-compose.yml:
    [ ] Adicionar serviço init-neo4j (one-shot, depends_on: neo4j healthy, restart: "no")
    [ ] Adicionar serviço init-seaweedfs (one-shot, depends_on: seaweedfs healthy, restart: "no")
```

**Validação:**
- [ ] `docker compose up -d` → init services exitam com código 0
- [ ] `docker compose exec postgres psql -U dataops -d dataops -c "\dt"` → 3 tabelas
- [ ] Neo4j Browser: `MATCH (n) RETURN count(n)` → nodes presentes
- [ ] `aws --endpoint-url http://localhost:8333 s3 ls s3://dataops-lake/` → bucket existe
- [ ] Docs seed em `infra/docs/` criados

---

## FASE 2 — DADOS

### Task 04 — Data Generator
**Prompt:** `prompts/5-build-data-generator.md`

```
[ ] generator/main.py — loop infinito (intervalo: GENERATOR_INTERVAL_SECONDS=30):
    [ ] PostgreSQL:
        [ ] 2-5 novos customers por ciclo (planos: 60% free, 30% pro, 10% enterprise)
        [ ] 5-15 novos orders por ciclo (status: 70% completed, 15% pending, 10% failed, 5% refunded)
        [ ] 1-3 novos products a cada 5 ciclos
    [ ] MongoDB:
        [ ] 3-8 event_logs por ciclo (pipeline_name, status, error_message, severity, duration_seconds, records_processed)
        [ ] 5-10 user_activity por ciclo (user_id, action, metadata, session_id)
    [ ] SeaweedFS:
        [ ] A cada 10 ciclos: upload de CSV report (reports/daily-summary-YYYY-MM-DD.csv)
    [ ] asyncio para writes concorrentes
    [ ] Graceful shutdown (SIGTERM/SIGINT)
    [ ] Logging estruturado
    [ ] Retry com backoff (3 tentativas)

[ ] generator/Dockerfile (python:3.11-slim)
[ ] generator/requirements.txt (faker, psycopg2-binary, pymongo, boto3, python-dotenv)
[ ] Atualizar docker-compose.yml com serviço data-generator (depends_on: postgres+mongo+seaweedfs healthy)
```

**Validação:**
- [ ] `docker compose up -d data-generator` sem erros
- [ ] `docker compose logs data-generator` → ciclos a cada 30s sem erros
- [ ] `SELECT count(*) FROM customers` aumenta ao longo do tempo
- [ ] `db.event_logs.countDocuments()` aumenta ao longo do tempo
- [ ] Graceful shutdown: `docker compose stop data-generator` → exit limpo

---

## FASE 3 — CONTRATOS

### Task 05 — Schemas Pydantic
**Prompt:** `prompts/6-build-pydantic-schemas.md`

```
[ ] src/schemas/domain.py — entidades de negócio:
    [ ] Enums: CustomerPlan(free|pro|enterprise), OrderStatus(pending|completed|failed|refunded)
    [ ] Enums: PipelineStatus(completed|failed|warning), Severity(info|warning|critical)
    [ ] Models: Customer, Order, PipelineEvent, PipelineNode, TableNode
    [ ] Model: DependencyChain (source, downstream_pipelines, downstream_tables, downstream_dashboards, impacted_teams)

[ ] src/schemas/query.py — output dos engines (usado como output_cls no LlamaIndex):
    [ ] LedgerQueryResult (sql_query_executed, summary, row_count, data_points)
    [ ] MemoryQueryResult (summary, sources, confidence[0.0-1.0], relevant_facts)
    [ ] BrainQueryResult (cypher_query_executed, summary, nodes_traversed, relationships_found, dependency_chain?)
    [ ] SynthesizedResponse (answer, sub_questions, sources_consulted, confidence[0.0-1.0], recommendation?)

[ ] src/schemas/api.py — contratos HTTP:
    [ ] QueryRequest (question, sources?[ledger|memory|brain], include_metadata)
    [ ] SourceDetail (source, data_store, query_used, result_summary, confidence[0.0-1.0])
    [ ] QueryResponse (question, answer, sub_questions, sources_consulted[SourceDetail], recommendation?, processing_time_ms, timestamp)
    [ ] HealthResponse (status, services{str:str}, uptime_seconds, version)

[ ] src/schemas/__init__.py — exporta tudo (from src.schemas.domain import *, etc.)
```

**Validação:**
- [ ] `python -c "from src.schemas import *"` sem import errors
- [ ] Todos os models têm Field(description=...) — crítico para LlamaIndex structured output
- [ ] Confidence usa `Field(ge=0.0, le=1.0)` — validação em runtime
- [ ] Nenhum import circular entre domain.py, query.py e api.py

---

## FASE 4 — INGESTÃO

### Task 06 — Ingestion Pipeline (Memory/Qdrant)
**Prompt:** `prompts/7-build-ingestion-pipeline.md`

```
[ ] src/ingestion/config.py — IngestionConfig (pydantic-settings):
    [ ] Campos: openai_api_key, llm_model, embedding_model
    [ ] Campos: qdrant_host, qdrant_port, qdrant_collection
    [ ] Campos: seaweedfs_host, seaweedfs_port, seaweedfs_bucket
    [ ] Campos: mongo_host, mongo_port, mongo_db
    [ ] Campos: chunk_size=512, chunk_overlap=50
    [ ] class Config: env_file=".env", extra="ignore"

[ ] src/ingestion/readers.py:
    [ ] SeaweedFSReader.load_data() → list[Document]
        [ ] Conecta via boto3 (S3-compat, endpoint_url=seaweedfs)
        [ ] Lista todos objetos no bucket
        [ ] Metadata: source_type="seaweedfs", file_name, file_type, upload_date
    [ ] MongoDBReader.load_data() → list[Document]
        [ ] Lê event_logs (últimas 24h) → Document com texto formatado
        [ ] Metadata: source_type="mongodb", collection="event_logs", pipeline_name, status, severity
        [ ] Lê user_activity (últimas 24h) → Document
        [ ] Metadata: source_type="mongodb", collection="user_activity", action, user_id
        [ ] Handle de erros: log warning + retorna lista vazia

[ ] src/ingestion/pipeline.py — IngestionPipeline LlamaIndex:
    [ ] Splitter: SemanticSplitterNodeParser (primário) + SentenceSplitter fallback
    [ ] Extractors: TitleExtractor(nodes=3), SummaryExtractor, KeywordExtractor(keywords=5), QuestionsAnsweredExtractor(questions=3)
    [ ] Embedding: OpenAIEmbedding(model="text-embedding-3-small")
    [ ] Storage: QdrantVectorStore (collection: dataops-memory)
    [ ] build_pipeline(config) → IngestionPipeline
    [ ] run_pipeline(pipeline, documents) → list[nodes]

[ ] src/ingestion/run.py — entry point:
    [ ] async main(): carrega docs → builda pipeline → roda → loga resultados
    [ ] if __name__ == "__main__": asyncio.run(main())
    [ ] Makefile: make ingest = python -m src.ingestion.run
```

**Validação:**
- [ ] `python -m src.ingestion.run` completa sem erros
- [ ] `curl http://localhost:6333/collections/dataops-memory` → collection existe
- [ ] `points_count > 0` na collection
- [ ] Cada ponto tem metadata (title, summary, keywords, questions_this_excerpt_can_answer)
- [ ] Docs de SeaweedFS e MongoDB representados na collection

---

## FASE 5 — QUERY ENGINES

### Task 07 — Query Engines (Ledger, Memory, Brain)
**Prompt:** `prompts/8-build-query-engines.md`

```
[ ] src/engines/config.py — EngineConfig (pydantic-settings):
    [ ] Campos: openai_api_key, llm_model, embedding_model
    [ ] Campos: postgres_host, postgres_port, postgres_db, postgres_user, postgres_password
    [ ] Campos: qdrant_host, qdrant_port, qdrant_collection
    [ ] Campos: neo4j_uri, neo4j_user, neo4j_password
    [ ] Property: postgres_connection_string → str

[ ] src/engines/ledger.py — LedgerEngine:
    [ ] Conecta PostgreSQL via SQLAlchemy
    [ ] SQLDatabase(include_tables=["customers", "orders", "products"])
    [ ] NLSQLTableQueryEngine(llm=OpenAI, synthesize_response=True)
    [ ] Table descriptions (customers, orders, products) para melhorar SQL gerado
    [ ] async query(question: str) → LedgerQueryResult
        [ ] Extrai sql_query de response.metadata["sql_query"]
        [ ] Retorna LedgerQueryResult validado

[ ] src/engines/memory.py — MemoryEngine:
    [ ] QdrantClient + QdrantVectorStore(collection=dataops-memory)
    [ ] VectorStoreIndex.from_vector_store(vector_store) — NÃO re-ingere
    [ ] query_engine com similarity_top_k=5, response_mode="tree_summarize"
    [ ] async query(question: str) → MemoryQueryResult
        [ ] Extrai source nodes (nomes, scores)
        [ ] Confidence = média dos scores
        [ ] Retorna MemoryQueryResult validado

[ ] src/engines/brain.py — BrainEngine:
    [ ] Neo4j driver (bolt) com schema context:
        Schema: Team, Pipeline, Table, Dashboard
        Relationships: OWNS, READS_FROM, WRITES_TO, FEEDS, USED_BY
    [ ] LLM gera Cypher a partir da pergunta (com exemplos no prompt)
    [ ] Executa Cypher no Neo4j
    [ ] LLM sintetiza resultado em linguagem natural
    [ ] async query(question: str) → BrainQueryResult
        [ ] cypher_query_executed preenchido
        [ ] dependency_chain populado quando query envolve dependências
    [ ] close() para fechar conexão Neo4j

[ ] Error handling em todos os engines:
    [ ] Store inacessível → raise com mensagem descritiva
    [ ] SQL/Cypher inválido → captura erro, loga, retorna summary com mensagem de erro
    [ ] Timeout: 30s por query
```

**Validação:**
- [ ] Ledger: `query("How many enterprise customers?")` → LedgerQueryResult com SQL válido
- [ ] Ledger: `query("Top 5 customers by total order amount")` → data_points com nomes e valores
- [ ] Memory: `query("What is the data retention policy for PII?")` → referencia retention-policy.md
- [ ] Memory: `query("What happened in the last pipeline failure?")` → referencia event_logs
- [ ] Brain: `query("What pipelines does team-billing own?")` → BrainQueryResult com Cypher
- [ ] Brain: `query("What would be impacted if orders table goes down?")` → dependency_chain populado
- [ ] Todos retornam Pydantic models (não strings raw)
- [ ] Todos completam em < 30s

---

### Task 08 — Router Engine
**Prompt:** `prompts/9-build-router-engine.md`

```
[ ] src/engines/router.py — RouterEngine:

    [ ] __init__(config: EngineConfig):
        [ ] self.llm = OpenAI(model=config.llm_model)
        [ ] self.ledger = LedgerEngine(config)
        [ ] self.memory = MemoryEngine(config)
        [ ] self.brain = BrainEngine(config)

    [ ] _classify(question: str) → list[{engine, sub_question}]:
        [ ] System prompt com descrição dos 3 domínios + regras de roteamento
        [ ] LLM retorna JSON: {sub_questions: [{engine, question}]}
        [ ] Máximo 3 sub-questions
        [ ] Fallback: todos os engines se resposta LLM for inválida

    [ ] _execute_sub_questions(sub_questions) → list[results]:
        [ ] asyncio.gather para execução paralela
        [ ] Trata falha por engine individualmente (não falha tudo)

    [ ] _build_source_detail(engine_name, result) → SourceDetail:
        [ ] Ledger: data_store="postgresql", query_used=sql_query, confidence=0.9
        [ ] Memory: data_store="qdrant", query_used="Vector search (top_k=5)", confidence=result.confidence
        [ ] Brain: data_store="neo4j", query_used=cypher_query, confidence=0.85

    [ ] _synthesize(original_question, results) → SynthesizedResponse:
        [ ] LLM sintetiza todos os resultados em resposta coesa
        [ ] Extrai recommendation se aplicável
        [ ] Confidence = média ponderada das engines

    [ ] async query(question: str, sources: list[str] | None = None) → tuple[SynthesizedResponse, list[SourceDetail]]:
        [ ] Se sources fornecido: pula classificação, vai direto para engines filtradas
        [ ] Se sources=None: classifica → decompõe → executa paralelo → sintetiza
        [ ] Retorna (SynthesizedResponse, list[SourceDetail])
```

**Validação:**
- [ ] Query simples → 1 engine (ex: "How many customers?" → ledger)
- [ ] Query complexa → decompõe em 3 sub-questions (ledger + memory + brain)
- [ ] `query(..., sources=["ledger"])` → ignora classificação, só usa ledger
- [ ] SynthesizedResponse.sub_questions mostra a decomposição
- [ ] SourceDetail.query_used mostra o SQL/Cypher/vector executado
- [ ] Query cross-domain completa em < 60s

---

## FASE 6 — SERVING

### Task 09 — FastAPI
**Prompt:** `prompts/10-build-fastapi.md`

```
[ ] src/api/app.py — create_app():
    [ ] @asynccontextmanager lifespan: inicializa RouterEngine uma vez (app.state.router)
    [ ] CORSMiddleware (all origins para dev)
    [ ] Middleware de request logging: "INFO: POST /api/v1/query → 200 (1234.56ms)"
    [ ] Include routers de src/api/routes/
    [ ] Metadata: title, version, description

[ ] src/api/routes/query.py:
    [ ] POST /api/v1/query (response_model=QueryResponse)
    [ ] time.perf_counter() para processing_time_ms
    [ ] Chama req.app.state.router.query(...)
    [ ] Mapeia (SynthesizedResponse, list[SourceDetail]) → QueryResponse

[ ] src/api/routes/health.py:
    [ ] GET /health (response_model=HealthResponse)
    [ ] Verifica cada serviço com timeout 5s:
        [ ] PostgreSQL: SELECT 1
        [ ] Qdrant: GET /healthz
        [ ] Neo4j: RETURN 1 via bolt
        [ ] MongoDB: ping
        [ ] SeaweedFS: GET /cluster/status
    [ ] Overall status: "healthy" só se postgres + qdrant + neo4j estiverem up
    [ ] uptime_seconds desde startup do app

[ ] src/api/routes/ingest.py:
    [ ] POST /api/v1/ingest (BackgroundTasks)
    [ ] Dispara ingestion em background
    [ ] Retorna 202: {status: "ingestion_started", job_id, message}

[ ] src/api/main.py:
    [ ] app = create_app()
    [ ] uvicorn.run(reload=True para dev)

[ ] Global exception handlers:
    [ ] asyncio.TimeoutError → 504 Gateway Timeout
    [ ] Exception (catch-all) → 500 sem vazar internals

[ ] OpenAPI: Field(json_schema_extra={"examples": [...]}) nos schemas
[ ] Atualizar docker-compose.yml com serviço app (depends_on: postgres+mongo+qdrant+neo4j healthy)
[ ] Criar Dockerfile para a app (python:3.11-slim, pip install ., CMD uvicorn)
```

**Validação:**
- [ ] `make serve` sobe em porta 8000
- [ ] `curl http://localhost:8000/health` → todos os serviços healthy
- [ ] `curl http://localhost:8000/docs` → Swagger UI com todos os endpoints
- [ ] `POST /api/v1/query {"question": "How many customers?"}` → QueryResponse válida
- [ ] Response inclui processing_time_ms, sub_questions, sources_consulted com query_used
- [ ] `POST /api/v1/ingest` → 202 imediato
- [ ] Body inválido → 422
- [ ] Timeout → 504

---

### Task 10 — MCP Server
**Prompt:** `prompts/11-build-mcp-server.md`

```
[ ] src/mcp/server.py — usando mcp Python SDK:
    [ ] Tool: query_knowledge_hub
        [ ] Description detalhada (menciona PostgreSQL/Qdrant/Neo4j e tipos de pergunta)
        [ ] Input schema: {question: str, sources?: array[ledger|memory|brain]}
        [ ] Handler: POST para {API_BASE_URL}/api/v1/query via httpx
        [ ] Formata resposta como Markdown legível (## Answer, ## Recommendation, ## Sources)
    [ ] Tool: check_platform_health
        [ ] Input schema: {} (sem parâmetros)
        [ ] Handler: GET para {API_BASE_URL}/health
    [ ] Tool: trigger_ingestion
        [ ] Input schema: {} (sem parâmetros)
        [ ] Handler: POST para {API_BASE_URL}/api/v1/ingest
    [ ] Transporte: stdio
    [ ] API_BASE_URL configurável via env var (default: http://localhost:8000)

[ ] src/mcp/run.py — entry point: python -m src.mcp.run

[ ] mcp-config.json na raiz (referência):
    [ ] Config local (API_BASE_URL: http://localhost:8000)
    [ ] Config produção (API_BASE_URL: http://<DROPLET_IP>:8000)

[ ] Atualizar pyproject.toml:
    [ ] "mcp>=1.0" nas dependências
    [ ] Script: dataops-mcp = "src.mcp.run:main"
```

**Validação:**
- [ ] `python -m src.mcp.run` inicia sem erros (aguarda em stdio)
- [ ] `echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python -m src.mcp.run` → 3 tools
- [ ] Tool call com query retorna resposta formatada em Markdown
- [ ] `claude mcp add dataops-knowledge-hub -- python -m src.mcp.run` funciona

---

## FASE 7 — TESTES

### Task 11 — Test Suite
**Prompt:** `prompts/12-build-tests.md`

```
[ ] tests/conftest.py:
    [ ] Fixture event_loop (session scope)
    [ ] Fixture config (carrega EngineConfig do .env)

[ ] tests/unit/test_schemas.py (sem infra):
    [ ] QueryRequest válido com todos os campos
    [ ] QueryRequest válido com apenas question
    [ ] QueryRequest inválido (sem question) → ValidationError
    [ ] QueryResponse com todos os SourceDetail
    [ ] SourceDetail.confidence rejeita > 1.0 e < 0.0
    [ ] Todos os Enums têm valores válidos
    [ ] DependencyChain com listas vazias é válido
    [ ] HealthResponse aceita service names arbitrários

[ ] tests/unit/test_router_classification.py (mock LLM):
    [ ] Pergunta sobre customers → routes to "ledger"
    [ ] Pergunta sobre SLA → routes to "memory"
    [ ] Pergunta sobre ownership → routes to "brain"
    [ ] Pergunta complexa → decompõe em 2-3 sub-questions
    [ ] Resposta LLM malformada → fallback para todos os engines
    [ ] sources filter → pula classificação

[ ] tests/integration/test_engines.py (@pytest.mark.integration):
    [ ] TestLedgerEngine: test_count_query, test_aggregation_query
    [ ] TestMemoryEngine: test_policy_query, test_event_query
    [ ] TestBrainEngine: test_ownership_query, test_dependency_query

[ ] tests/integration/test_router.py (@pytest.mark.integration):
    [ ] test_single_engine_routing
    [ ] test_multi_engine_routing
    [ ] test_forced_routing

[ ] tests/integration/test_api.py (@pytest.mark.integration, httpx):
    [ ] test_health_endpoint
    [ ] test_query_endpoint
    [ ] test_query_with_sources_filter
    [ ] test_invalid_request → 422
    [ ] test_ingest_endpoint → 202

[ ] pytest.ini (ou pyproject.toml):
    [ ] asyncio_mode = "auto"
    [ ] markers: integration
    [ ] testpaths = ["tests"]

[ ] Makefile atualizado:
    [ ] make test = pytest tests/unit -v
    [ ] make test-integration = pytest tests/integration -v --timeout=120
    [ ] make test-all = pytest tests/ -v --timeout=120
```

**Validação:**
- [ ] `make test` → todos os unit tests passam (sem infra)
- [ ] `make test-integration` → todos passam (com stack rodando)
- [ ] Nenhum teste demora mais de 60s individualmente
- [ ] Unit tests mockam dependências externas
- [ ] Assertions checam Pydantic models (não apenas dict shapes)

---

## FASE 8 — VALIDAÇÃO LOCAL

### Task 12 — Full Local Validation
**Prompt:** `prompts/13-run-dev.md`

```
[ ] Step 1 — Infraestrutura:
    [ ] cp .env.example .env + adicionar OPENAI_API_KEY
    [ ] make up → todos os serviços healthy
    [ ] Verificar cada serviço individualmente (pg_isready, mongosh ping, qdrant healthz, neo4j, seaweedfs)

[ ] Step 2 — Verificar Init Scripts:
    [ ] PostgreSQL: \dt mostra 3 tabelas com schema correto
    [ ] Neo4j: MATCH (n) RETURN count(n) → nodes presentes
    [ ] SeaweedFS: bucket dataops-lake com 4 docs seed

[ ] Step 3 — Verificar Data Generator:
    [ ] docker compose logs data-generator → ciclos sem erros
    [ ] Contagens aumentam ao longo do tempo (Postgres + MongoDB)

[ ] Step 4 — Ingestão:
    [ ] make ingest → completa sem erros
    [ ] Qdrant collection dataops-memory com pontos indexados

[ ] Step 5 — Testar engines individualmente:
    [ ] Script Python: LedgerEngine.query, MemoryEngine.query, BrainEngine.query
    [ ] Todos retornam Pydantic models corretos

[ ] Step 6 — Testar Router (cross-domain):
    [ ] Query simples → 1 engine
    [ ] Query complexa → 3 engines em paralelo
    [ ] Forced routing via sources filter

[ ] Step 7 — Testar FastAPI:
    [ ] make serve &
    [ ] curl /health → all healthy
    [ ] curl POST /api/v1/query → QueryResponse válida
    [ ] Query cross-domain → múltiplos sources_consulted
    [ ] Swagger /docs funcional

[ ] Step 8 — Testes automáticos:
    [ ] make test → unit tests passam
    [ ] make test-integration → integration tests passam

[ ] Step 9 — Testar MCP Server localmente:
    [ ] python -m src.mcp.run → inicia sem erros
    [ ] tools/list → 3 tools
    [ ] tools/call query_knowledge_hub → resposta formatada
    [ ] Adicionar ao Claude Code + testar via terminal

[ ] Step 10 — Fix de bugs:
    [ ] Qualquer falha nos steps acima deve ser corrigida antes de avançar
```

**Critério de sucesso para avançar ao deploy:**
- [ ] Todos os 5 serviços de infra healthy
- [ ] Data generator produzindo dados continuamente
- [ ] 3 engines respondem corretamente
- [ ] Router decompõe e roteia queries cross-domain
- [ ] FastAPI serve sem erros
- [ ] MCP expõe tools corretamente
- [ ] Todos os testes passam
- [ ] Query cross-domain completa em < 30s

---

## FASE 9 — DEPLOY

### Task 13 — Deploy DigitalOcean
**Prompt:** `prompts/14-build-deploy.md`

```
[ ] Remover railway.toml

[ ] scripts/deploy-digitalocean.sh:
    [ ] Verifica prerequisitos: doctl autenticado, .env.production existe
    [ ] Auto-detecta SSH key do DO account
    [ ] Cria Droplet s-2vcpu-4gb em nyc1 com docker-20-04 (ou reutiliza existente)
    [ ] Aguarda SSH disponível
    [ ] Copia .env.production para droplet via SCP
    [ ] Remote: git clone/pull, setup env, docker compose pull + build + up
    [ ] Remote: init scripts, aguarda data generator (30s), roda ingestão
    [ ] Verifica health da API
    [ ] Exibe summary: IP, URLs, SSH, MCP config

[ ] scripts/destroy-digitalocean.sh:
    [ ] Confirmação interativa antes de destruir
    [ ] doctl compute droplet delete

[ ] scripts/deploy.sh (deploy genérico com Docker):
    [ ] Funciona em qualquer máquina com Docker
    [ ] Valida .env (sem senhas placeholder)
    [ ] Pull + build + up + init + ingest + health check

[ ] docker-compose.production.yml:
    [ ] Igual ao dev mas com restart: always
    [ ] Sem portas expostas desnecessariamente
    [ ] Sem volume mounts de código (usa image buildada)

[ ] .env.production.example:
    [ ] OPENAI_API_KEY
    [ ] POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD (senhas fortes)
    [ ] MONGO_DB
    [ ] NEO4J_USER, NEO4J_PASSWORD (senha forte)
    [ ] APP_PORT, LLM_MODEL, EMBEDDING_MODEL

[ ] mcp-config.json atualizado:
    [ ] Entrada local (localhost:8000)
    [ ] Entrada produção (<DROPLET_IP>:8000)

[ ] Makefile atualizado:
    [ ] make deploy-do, make destroy-do, make deploy-local
    [ ] make prod-up, make prod-down, make prod-logs, make prod-restart, make prod-status, make prod-ingest

[ ] README.md atualizado com instruções DigitalOcean
```

**Validação:**
- [ ] `bash -n scripts/deploy-digitalocean.sh` → syntax check ok
- [ ] `docker compose -f docker-compose.production.yml config` → valida
- [ ] Makefile tem todos os targets novos
- [ ] `make deploy-do` executa sem erros
- [ ] `curl http://<DROPLET_IP>:8000/health` → API pública healthy
- [ ] MCP Server apontando para produção funciona via Claude Code
- [ ] Sem referências ao Railway em nenhum arquivo

---

## GRAND FINALE

```
[ ] API pública respondendo em http://<DROPLET_IP>:8000
[ ] MCP config atualizado com URL de produção
[ ] Claude Code conectado ao MCP Server de produção:
    claude mcp add dataops-knowledge-hub-prod -- python -m src.mcp.run

[ ] Executar a query final no Claude Code:
    "Use the dataops-knowledge-hub tool to find out which customers are on
    the enterprise plan, what the SLA is for the billing pipeline, and what
    would happen if the orders table went down."

[ ] Verificar resposta:
    [ ] sub_questions mostra decomposição em 3 perguntas
    [ ] sources_consulted mostra ledger + memory + brain
    [ ] query_used mostra o SQL, vector search e Cypher executados
    [ ] Resposta coesa combinando os 3 domínios
    [ ] Recommendation acionável presente
    [ ] processing_time_ms < 30000
```

**O AI Agent consome o sistema que ele mesmo construiu.**

---

## CHECKLIST FINAL

- [ ] `docker compose up -d` → todos os serviços healthy
- [ ] Data generator rodando continuamente
- [ ] Ingestão completa (Qdrant com pontos)
- [ ] 3 engines respondem com Pydantic models válidos
- [ ] Router decompõe queries cross-domain
- [ ] `GET /health` → 200
- [ ] `POST /api/v1/query` → valida schema, rejeita requests inválidos
- [ ] `POST /api/v1/ingest` → 202 imediato
- [ ] MCP registrado e respondendo no Claude Code
- [ ] `make test` → unit tests verdes
- [ ] `make test-integration` → integration tests verdes
- [ ] Deploy DigitalOcean → API pública acessível
- [ ] Grand Finale executado com sucesso no terminal
