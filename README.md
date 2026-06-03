# AI Engineering Projects

This is the repo where I build and document my AI Engineering projects — production-grade systems combining LLMs, RAG pipelines, vector databases, graph databases, and agentic frameworks.

---

## Projects

| # | Project | Stack | Description |
|---|---------|-------|-------------|
| 01 | [DataOps Knowledge Hub](./llama-index-rag) | LlamaIndex · FastAPI · PostgreSQL · Qdrant · Neo4j · MongoDB · SeaweedFS | Enterprise RAG system that answers natural language questions by routing them across three specialized data stores |

---

## About Me

I am an electrical engineer turned data scientist and AI engineer who loves building data-driven systems that make an impact on business and society.

My journey started at the Applied Computational Intelligence Laboratory (Fluminense Federal University), where I built Artificial Neural Network models for power forecasting. A scholarship took me to the University of Toronto, after which I worked with electrical projects, project management, and substation construction in Brazil and abroad.

Over the years I transitioned from classical machine learning into data engineering and, more recently, into AI Engineering — building production systems with LLMs, RAG pipelines, and agentic frameworks.

### 01 · DataOps Knowledge Hub
An enterprise-grade, multi-source RAG system built for the AIDE Brasil Workshop. It answers natural language questions by intelligently routing them across three specialized engines:

- **Ledger** (PostgreSQL) — factual and numerical queries via LLM-generated SQL
- **Memory** (Qdrant) — document, policy, and event log search via vector embeddings
- **Brain** (Neo4j) — relationship, lineage, and ownership queries via LLM-generated Cypher

A `RouterEngine` classifies each question, decomposes complex queries into sub-questions, executes them in parallel with `asyncio.gather`, and synthesizes a unified Pydantic-validated response. The system is served via **FastAPI** and exposed as an **MCP tool** so AI Agents (Claude Code) can consume it natively.

**Stack:** LlamaIndex 0.14 · Pydantic v2 · FastAPI · OpenAI GPT-4.1-mini · text-embedding-3-small · Docker Compose · Python 3.13

---

## Connect

- [LinkedIn](https://www.linkedin.com/in/jonathancabreira)
- [GitHub](https://github.com/jmcabreira)
