"""LlamaIndex ingestion pipeline: chunk → enrich → embed → store in Qdrant."""
import logging
import time

from llama_index.core.extractors import (
    KeywordExtractor,
    QuestionsAnsweredExtractor,
    SummaryExtractor,
    TitleExtractor,
)
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SemanticSplitterNodeParser, SentenceSplitter
from llama_index.core.schema import Document
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.models import Distance, VectorParams

from src.ingestion.config import IngestionConfig

log = logging.getLogger(__name__)


def _ensure_collection(client: QdrantClient, name: str, vector_size: int = 1536) -> None:
    """Create Qdrant collection if it does not exist."""
    existing = {c.name for c in client.get_collections().collections}
    if name not in existing:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        log.info("Created Qdrant collection '%s'", name)
    else:
        log.info("Qdrant collection '%s' already exists", name)


def build_pipeline(config: IngestionConfig) -> IngestionPipeline:
    """Construct and return the LlamaIndex IngestionPipeline."""
    embed_model = OpenAIEmbedding(
        model=config.embedding_model,
        api_key=config.openai_api_key,
    )
    llm = OpenAI(model=config.llm_model, api_key=config.openai_api_key)

    semantic_splitter = SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=95,
        embed_model=embed_model,
    )
    fallback_splitter = SentenceSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )

    qdrant_client = QdrantClient(host=config.qdrant_host, port=config.qdrant_port)
    async_qdrant_client = AsyncQdrantClient(host=config.qdrant_host, port=config.qdrant_port)
    # text-embedding-3-small produces 1536-dim vectors
    _ensure_collection(qdrant_client, config.qdrant_collection, vector_size=1536)
    vector_store = QdrantVectorStore(
        client=qdrant_client,
        aclient=async_qdrant_client,
        collection_name=config.qdrant_collection,
    )

    pipeline = IngestionPipeline(
        transformations=[
            semantic_splitter,
            TitleExtractor(nodes=3, llm=llm),
            SummaryExtractor(summaries=["self"], llm=llm),
            KeywordExtractor(keywords=5, llm=llm),
            QuestionsAnsweredExtractor(questions=3, llm=llm),
            embed_model,
        ],
        vector_store=vector_store,
    )
    return pipeline


async def run_pipeline(pipeline: IngestionPipeline, documents: list[Document]) -> list:
    """Run the pipeline and return the list of indexed nodes."""
    if not documents:
        log.warning("No documents to ingest — skipping pipeline run")
        return []

    log.info("Running ingestion pipeline on %d documents...", len(documents))
    start = time.monotonic()
    nodes = await pipeline.arun(documents=documents)
    elapsed = time.monotonic() - start
    log.info("Pipeline complete in %.1fs — %d nodes indexed", elapsed, len(nodes))
    return nodes
