# DataOps Knowledge Hub

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![LlamaIndex](https://img.shields.io/badge/LlamaIndex-0.12+-green.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

Enterprise RAG system demonstrating multi-source retrieval across structured, semi-structured, and unstructured data stores.

## Architecture

```
Question → RouterEngine → [Ledger | Memory | Brain] → SynthesizedResponse
```

| Domain | Store | Retrieval | Use case |
|--------|-------|-----------|----------|
| **Ledger** | PostgreSQL | Text-to-SQL | Counts, revenue, orders |
| **Memory** | Qdrant | Vector search | Policies, logs, runbooks |
| **Brain** | Neo4j | Graph traversal | Lineage, ownership, dependencies |

## Quick Start

```bash
cp .env.example .env
# Add your OPENAI_API_KEY to .env

make up        # start all services
make ingest    # index documents into Qdrant
make serve     # start FastAPI on :8000
make query     # interactive query via CLI
```

## Stack

LlamaIndex · Pydantic v2 · FastAPI · PostgreSQL · Qdrant · Neo4j · MongoDB · SeaweedFS · Docker · MCP

## Project Structure

```
src/
├── schemas/    ← Pydantic contracts (domain, query, api)
├── ingestion/  ← LlamaIndex ingestion pipeline (Memory only)
├── engines/    ← ledger, memory, brain, router
├── api/        ← FastAPI app + routes
└── mcp/        ← MCP Server for AI Agents
```

## Commands

```bash
make test              # unit tests
make test-integration  # integration tests (requires stack running)
make deploy-do         # deploy to DigitalOcean
```

---

*Part of the Intelligent DataOps Platform — AIDE Brasil Formation (W01)*
