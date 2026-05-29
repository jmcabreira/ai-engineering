# LlamaIndex RAG

A Retrieval-Augmented Generation (RAG) pipeline built with [LlamaIndex](https://www.llamaindex.ai/) and Claude (Anthropic).

## Overview

This project implements a RAG system that allows you to query your own documents using natural language. Documents are indexed and stored in a vector database; at query time, relevant chunks are retrieved and passed to an LLM to generate accurate, grounded answers.

## Features

- Document ingestion (PDF, TXT, Markdown, HTML)
- Vector indexing with LlamaIndex
- Semantic search and retrieval
- Answer generation via Claude (Anthropic API)
- Configurable chunking and embedding strategies

## Tech Stack

| Component | Technology |
|-----------|-----------|
| RAG Framework | LlamaIndex |
| LLM | Claude (Anthropic) |
| Embeddings | OpenAI / HuggingFace |
| Vector Store | ChromaDB / FAISS |
| Language | Python 3.11+ |

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) or pip
- Anthropic API key

### Installation

```bash
git clone https://github.com/your-username/llama-index-rag.git
cd llama-index-rag

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
```

Edit `.env`:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key  # if using OpenAI embeddings
```

### Usage

**Index documents:**

```bash
python ingest.py --source ./docs
```

**Query:**

```bash
python query.py "What does the document say about X?"
```

## Project Structure

```
llama-index-rag/
├── docs/               # Source documents to be indexed
├── storage/            # Persisted vector index
├── ingest.py           # Document ingestion pipeline
├── query.py            # Query interface
├── config.py           # Settings and configuration
├── requirements.txt
└── .env.example
```

## License

MIT
