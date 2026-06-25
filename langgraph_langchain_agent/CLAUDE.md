# CLAUDE.md — DataOps Knowledge Hub

## 1. Project Overview

The **DataOps Knowledge Hub** is a production-grade, multi-source RAG system that answers natural language questions by intelligently routing them across three specialized data stores: **Ledger** (PostgreSQL — factual/numerical data), **Memory** (Qdrant — documents, policies, logs), and **Brain** (Neo4j — relationships, lineage, ownership). A `RouterEngine` classifies each question, decomposes complex queries into sub-questions, executes them in parallel, and synthesizes a unified Pydantic-validated response. The system is served via FastAPI and exposed as an MCP tool so AI Agents (Claude Code) can consume it natively.

---

## 2. Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| RAG Framework | LlamaIndex | >= 0.12 |
| Data Contracts | Pydantic | v2 |
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

---

## 3. Architecture Rules

- **Todo output de LLM passa por Pydantic** — zero dicts soltos nas bordas do sistema.
- **Nunca use raw strings** como resposta de LLMs — sempre `output_cls` ou parser estruturado.
- **Cada query engine retorna um typed response** (`LedgerQueryResult`, `MemoryQueryResult`, `BrainQueryResult`).
- Use `SubQuestionQueryEngine` ou `RouterEngine` customizado para queries cross-domain.
- Use `IngestionPipeline` (não indexação manual) para ingestão de documentos.
- Prefira **semantic chunking** (`SemanticSplitterNodeParser`) sobre fixed-size.
- Todos os endpoints FastAPI têm `request_model` e `response_model` Pydantic.
- **PostgreSQL e Neo4j não passam por ingestão vetorial** — são consultados diretamente via SQL e Cypher.
- A ingestão no Qdrant é exclusiva para documentos do SeaweedFS e logs do MongoDB.

---

## 4. Code Standards

- **Python 3.11+**
- `async/await` em toda a aplicação — FastAPI e LlamaIndex suportam async nativamente.
- Type hints em todas as funções públicas.
- Docstrings em todas as funções e classes públicas.
- Dependências gerenciadas via `pyproject.toml` (não `requirements.txt`).
- Layout `src/` — todo código da aplicação em `src/`.
- Variáveis de ambiente via arquivo `.env` + `pydantic-settings` — **nunca hardcode secrets**.
- Nenhum nome de modelo hardcoded — use `LLM_MODEL` e `EMBEDDING_MODEL` via env.

---

## 5. Project Structure

```
dataops-knowledge-hub/
├── src/
│   ├── schemas/      ← contratos Pydantic (domain, query, api)
│   ├── ingestion/    ← pipeline LlamaIndex (só Memory/Qdrant)
│   ├── engines/      ← ledger, memory, brain, router
│   ├── api/          ← FastAPI app + routes
│   └── mcp/          ← MCP Server (stdio)
├── generator/        ← data generator contínuo (Docker)
├── infra/            ← scripts SQL, Cypher, seed docs
├── tests/            ← unit + integration
├── sketch/           ← plan.md (arquitetura) + tasks.md (checklist)
├── prompts/          ← prompts sequenciais de build (01–14)
├── docs/             ← material de referência
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

Referência completa: `sketch/plan.md`.

---

## 6. Naming Conventions

| Escopo | Convenção | Exemplo |
|--------|-----------|---------|
| Arquivos Python | `snake_case.py` | `ledger_engine.py` |
| Classes | `PascalCase` | `LedgerEngine` |
| Pydantic models | Sufixo descritivo | `QueryRequest`, `LedgerQueryResult`, `EngineConfig` |
| API routes | `/kebab-case` | `/api/v1/query`, `/health` |
| Docker services | `kebab-case` | `data-generator`, `neo4j` |
| Env vars | `UPPER_SNAKE_CASE` | `OPENAI_API_KEY`, `NEO4J_URI` |

---

## 7. Testing

- Framework: `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`).
- **Unit tests** (`tests/unit/`) — sem infra, mockam LLM e databases.
- **Integration tests** (`tests/integration/`) — marcados com `@pytest.mark.integration`, requerem stack completa rodando.
- Cada engine deve ser testado em isolamento antes dos testes de integração do router.
- Teste end-to-end obrigatório: uma query cross-domain deve retornar `SynthesizedResponse` válido com `sub_questions` e `sources_consulted` de múltiplos engines.
- Comandos: `make test` (unit) · `make test-integration` · `make test-all`.

---

## 8. Key References

- **Arquitetura e decisões de design:** `sketch/plan.md`
- **Checklist de build:** `sketch/tasks.md`
- **Material de referência do workshop:** `docs/w1-rag-content.md`
- **LlamaIndex docs:** https://docs.llamaindex.ai
- **Pydantic v2 docs:** https://docs.pydantic.dev

---

## 9. Workflow

1. Ler o prompt atual em `prompts/` (numerados sequencialmente: `01`, `02`, ..., `14`).
2. Executar **uma task por vez** conforme `sketch/tasks.md`.
3. Após completar cada task, apresentar resumo do que foi feito e marcar `[x]` no `tasks.md`.
4. **Não avançar para a próxima task sem confirmação do usuário.**
5. Se encontrar ambiguidade, consultar `sketch/plan.md` antes de decidir.
6. Ao terminar cada fase, rodar as validações listadas no `tasks.md` antes de prosseguir.

---

## 10. Constraints

- **NÃO use LangChain** — este projeto usa LlamaIndex exclusivamente.
- **NÃO use ChromaDB** — use Qdrant como vector store.
- **NÃO use in-memory vector stores em código de produção** — apenas em testes unitários.
- **NÃO hardcode nomes de modelos** — use variáveis de ambiente (`LLM_MODEL`, `EMBEDDING_MODEL`).
- **NÃO crie frontend/UI** — o sistema é API-only (FastAPI + MCP).
- **NÃO ingira dados do PostgreSQL ou Neo4j no Qdrant** — eles são consultados diretamente.
- **NÃO misture responsabilidades** — `RouterEngine` orquestra, engines consultam, API serve.


## MCP Tools Available
This project exposes a local MCP server (`dataops-knowledge-hub`).
When asked business questions about customers, pipelines, SLAs, revenue,
data quality, or infrastructure impact — ALWAYS use the
`
query_
knowledge
hub`
_
MCP tool instead of trying to answer from code or documentation.
Available MCP tools:
`
-
query_
knowledge
hub`
_
Postgres/Qdrant/Neo4j)
-
`
check
_platform
_
health`
-
`trigger
_
ingestion
`
— Ask any business question (routes to
— Check status of all data stores
— Re-index documents from SeaweedFS and MongoDB