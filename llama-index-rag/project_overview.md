# DataOps Knowledge Hub — Project Overview

## Estratégia

O sistema responde perguntas em linguagem natural sobre dados operacionais roteando cada pergunta para o store certo — ou para múltiplos stores em paralelo quando a pergunta cruza domínios. O LLM nunca responde "de cabeça": ele gera SQL/Cypher e busca em vetores; a resposta sempre parte de dados reais.

A arquitetura foi organizada em três "personalidades" de dados:

| Engine | Store | Responde |
|--------|-------|----------|
| **Ledger** | PostgreSQL | Fatos numéricos: contagens, receita, pedidos, segmentos |
| **Memory** | Qdrant | Documentos e eventos: políticas, SLAs, runbooks, logs de pipeline |
| **Brain** | Neo4j | Relações: ownership, lineage, análise de impacto |

Toda saída de LLM passa por um contrato Pydantic antes de sair do sistema. Nunca há `dict` solto nas bordas.

---

## Fluxo de uma pergunta

```
Usuário / AI Agent (MCP)
        ↓
   POST /api/v1/query
        ↓
   RouterEngine._classify()         ← LLM decompõe em sub-questions por engine
        ↓
   asyncio.gather(engines...)        ← execução paralela
   ┌────────┬──────────┬──────────┐
   Ledger   Memory     Brain
   SQL gen  Vec search Cypher gen
        ↓
   RouterEngine._synthesize()       ← LLM une os resultados (só se >1 engine)
        ↓
   SynthesizedResponse (Pydantic)
        ↓
   QueryResponse (Pydantic) → HTTP 200
```

---

## Estrutura de pastas

```
.
├── src/                    ← toda a aplicação
│   ├── schemas/            ← contratos Pydantic (domain, query, api)
│   ├── engines/            ← os três engines + router + config
│   ├── ingestion/          ← pipeline LlamaIndex (só para Qdrant)
│   ├── api/                ← FastAPI: app factory + rotas
│   └── mcp/                ← MCP server (stdio)
│
├── generator/              ← container de dados sintéticos contínuos
├── infra/
│   ├── scripts/            ← SQL, Cypher, shell para init dos stores
│   └── docs/               ← documentos que alimentam o Memory (SLA, runbooks, etc.)
├── tests/
│   ├── unit/               ← sem infra, mocks de LLM
│   └── integration/        ← requerem stack completa rodando
├── sketch/
│   ├── plan.md             ← decisões de arquitetura
│   └── tasks.md            ← checklist de build
├── prompts/                ← prompts sequenciais usados para construir o sistema (01–14)
├── docker-compose.yml      ← 8 containers orquestrados
├── Dockerfile              ← imagem da aplicação FastAPI
└── pyproject.toml          ← dependências e entrypoints
```

---

## `src/schemas/` — Contratos Pydantic

Três arquivos, cada um com uma responsabilidade:

**`domain.py`** — entidades de negócio puras. `Customer`, `Order`, `PipelineEvent`, `PipelineNode`, `TableNode`, `DependencyChain`. Nenhuma lógica aqui, só estrutura.

**`query.py`** — o que cada engine retorna. `LedgerQueryResult` carrega o SQL executado. `MemoryQueryResult` carrega o confidence score e as fontes. `BrainQueryResult` carrega o Cypher e a dependency chain. `SynthesizedResponse` é o output final do router — inclui sub_questions e sources_consulted.

**`api.py`** — contratos HTTP. `QueryRequest` aceita `sources` opcional para forçar engines específicos. `QueryResponse` inclui `processing_time_ms`. `HealthResponse` agrega status dos 5 serviços.

**Por que Pydantic em tudo:** LLMs produzem texto livre. Forçar validação na saída de cada engine garante que o router recebe dados previsíveis, e que a API nunca vaza estrutura interna.

---

## `src/engines/` — Os Quatro Engines

**`config.py`** — `EngineConfig` via `pydantic-settings`. Lê tudo do `.env`, expõe `postgres_connection_string` como property. Nenhuma credencial no código.

**`ledger.py`** — `LedgerEngine`. Usa `NLSQLTableQueryEngine` do LlamaIndex. Cada tabela tem uma descrição semântica que guia o LLM na geração do SQL (`_TABLE_DESCRIPTIONS`). Timeout de 30s, retorna o SQL gerado junto com a resposta para rastreabilidade.

**`memory.py`** — `MemoryEngine`. `VectorStoreIndex` apontando para Qdrant. `similarity_top_k=5`, `response_mode="tree_summarize"`. O confidence score é a média dos scores de similaridade dos nodes recuperados. Extrai o nome da fonte dos metadados de cada node.

**`brain.py`** — `BrainEngine`. Dois LLM calls por query: (1) gera Cypher a partir de um prompt com o schema completo do grafo; (2) sintetiza os records retornados. Detecta automaticamente perguntas de impacto/lineage (keywords como "downstream", "impacted") e monta um `DependencyChain` estruturado.

**`router.py`** — `RouterEngine`. Orquestra tudo.
- `_classify()`: LLM com prompt fixo decompõe a pergunta em até 3 sub-questions, uma por engine. Fallback para `memory` se a classificação falhar.
- Execução via `asyncio.gather()` — todos os engines em paralelo.
- Otimização: se só 1 engine foi chamado e retornou sem erro, o LLM de síntese é pulado.
- `_synthesize()`: LLM une os resultados; separa automaticamente "Recommendation:" do corpo da resposta.
- Confidence final: média dos scores dos engines consultados.

---

## `src/ingestion/` — Pipeline para o Qdrant

**Por que só o Qdrant precisa de ingestão:** PostgreSQL e Neo4j são consultados diretamente por SQL e Cypher. Apenas documentos e logs precisam virar vetores.

**`readers.py`** — dois readers:
- `SeaweedFSReader`: lista objetos do bucket S3 e carrega como `Document` com metadados (file_name, file_type, upload_date).
- `MongoDBReader`: puxa `event_logs` e `user_activity` das últimas 24 horas, serializa cada documento MongoDB como texto estruturado.

**`pipeline.py`** — `build_pipeline()` monta o `IngestionPipeline` com 5 transformações em sequência:
1. `SemanticSplitterNodeParser` — chunking semântico (percentil 95), sem corte arbitrário de tokens
2. `TitleExtractor` — extrai título dos chunks
3. `SummaryExtractor` — resume cada chunk para melhorar retrieval
4. `KeywordExtractor` — 5 keywords por chunk
5. `QuestionsAnsweredExtractor` — 3 perguntas que o chunk responde (melhora match semântico)
6. `OpenAIEmbedding` — gera vetor 1536-dim e persiste no Qdrant

Cria a collection automaticamente se não existir.

**`run.py`** — entrypoint CLI para rodar ingestão manualmente fora da API.

---

## `src/api/` — FastAPI

**`app.py`** — factory `create_app()`. Usa `lifespan` do FastAPI para inicializar o `RouterEngine` na startup e fechar o driver Neo4j no shutdown. Registra middleware de log com tempo de resposta. Exception handlers para timeout (504) e genérico (500).

**`routes/query.py`** — `POST /api/v1/query`. Recebe `QueryRequest`, chama `router.query()`, retorna `QueryResponse`. Mede `processing_time_ms` localmente.

**`routes/health.py`** — `GET /health`. Verifica os 5 serviços em paralelo com timeout individual de 5s cada. PostgreSQL, Qdrant e Neo4j são críticos — se um falhar, o status geral é `"degraded"`. MongoDB e SeaweedFS são informativos.

**`routes/ingest.py`** — `POST /api/v1/ingest`. Retorna imediatamente com um `job_id` e roda a ingestão em background via `BackgroundTasks`. Progresso acompanhado pelos logs do servidor.

---

## `src/mcp/` — MCP Server

Expõe o hub como 3 tools para AI Agents (como o Claude Code) via protocolo stdio:

- `query_knowledge_hub` — chama `POST /api/v1/query` e formata a resposta em Markdown
- `check_platform_health` — chama `GET /health`
- `trigger_ingestion` — chama `POST /api/v1/ingest`

O MCP server é uma camada fina: recebe chamadas de tool e as traduz em requests HTTP para a FastAPI. `API_BASE_URL` configurável via env. O entrypoint `dataops-mcp` está registrado no `pyproject.toml`.

---

## `generator/` — Dados Sintéticos

Container Docker que roda indefinidamente a cada 30 segundos (configurável). A cada ciclo:
- **PostgreSQL**: insere 2–5 clientes e 5–15 pedidos. A cada 5 ciclos, cria 1–3 novos produtos.
- **MongoDB**: insere 3–8 eventos de pipeline e 5–10 registros de user_activity.
- **SeaweedFS**: a cada 10 ciclos, grava um CSV com métricas diárias.

Usa `Faker("pt_BR")` para nomes e emails realistas. Retry com backoff exponencial em cada store. Graceful shutdown via SIGTERM.

**Por que existe:** garante que o sistema sempre tem dados para responder perguntas, mesmo em dev/staging. Em produção, seria substituído pelos pipelines reais.

---

## `infra/` — Inicialização dos Stores

**`scripts/init-databases.sql`** — schema PostgreSQL: tabelas `customers`, `products`, `orders` com FK e índices. Roda automaticamente na primeira inicialização do container postgres.

**`scripts/init-neo4j.cypher`** + **`seed-neo4j.sh`** — cria nós (Team, Pipeline, Table, Dashboard) e relacionamentos (OWNS, READS_FROM, WRITES_TO, FEEDS, USED_BY) no Neo4j. Roda como container one-shot `init-neo4j`.

**`scripts/init-seaweedfs.sh`** — cria o bucket `dataops-lake` e faz upload inicial dos documentos da pasta `infra/docs/`. Roda como container one-shot `init-seaweedfs`.

**`docs/`** — documentos estáticos que alimentam o Memory engine: `sla-definitions.md`, `incident-response-runbook.md`, `data-retention-policy.md`, `data-dictionary.csv`.

---

## `docker-compose.yml` — Stack Completa

8 containers em rede bridge `dataops-network`:

| Container | Função |
|-----------|--------|
| `postgres` | Ledger — schema criado via init SQL |
| `mongo` | Logs de pipeline e user_activity |
| `qdrant` | Vector store do Memory engine |
| `neo4j` | Grafo do Brain engine (com plugin APOC) |
| `seaweedfs` | Data lake S3-compatível |
| `init-neo4j` | One-shot: semeia grafo |
| `init-seaweedfs` | One-shot: cria bucket e sobe docs |
| `data-generator` | Loop contínuo de dados sintéticos |
| `app` | FastAPI — sobe só após todos os stores estarem healthy |

Todos os stores críticos têm `healthcheck` configurado. O container `app` declara `depends_on` com `condition: service_healthy` para os 4 stores que usa.

---

## `tests/`

**`unit/`** — rodam sem infraestrutura.
- `test_schemas.py`: valida que os contratos Pydantic aceitam e rejeitam dados corretamente.
- `test_router_classification.py`: testa a lógica de classificação do router com LLM mockado.

**`integration/`** — marcados com `@pytest.mark.integration`, requerem stack rodando.
- `test_engines.py`: cada engine isolado com stores reais.
- `test_router.py`: query cross-domain deve retornar `SynthesizedResponse` com `sub_questions` e `sources_consulted` de múltiplos engines.
- `test_api.py`: endpoints HTTP end-to-end.

---

## Decisões de design em resumo

| Decisão | Motivo |
|---------|--------|
| LlamaIndex (não LangChain) | API mais próxima de índices e engines; integração nativa com Qdrant, Neo4j e SQL |
| Pydantic em toda borda | LLM output é imprevisível; validação estrutural elimina bugs silenciosos |
| Três stores especializados | Cada tipo de dado tem engine de busca ideal; um vetor store único seria péssimo para SQL e grafos |
| PostgreSQL/Neo4j sem ingestão vetorial | SQL e Cypher já são linguagens de query precisas; vetorizar dados estruturados piora a qualidade |
| RouterEngine com asyncio.gather | Queries independentes não precisam esperar uma pela outra; latência total = latência do engine mais lento |
| MCP Server sobre FastAPI (não direto) | FastAPI é testável via HTTP; MCP é só uma camada de tradução; os dois coexistem independentemente |
| Gerador de dados em container separado | Isolamento: o app não conhece como os dados chegam; em prod basta trocar o container |
