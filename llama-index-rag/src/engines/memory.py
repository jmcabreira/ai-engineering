"""Memory Engine — Vector similarity search backed by Qdrant."""
import asyncio
import logging

from llama_index.core import VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from src.engines.config import EngineConfig
from src.schemas.query import MemoryQueryResult

log = logging.getLogger(__name__)


class MemoryEngine:
    """Answers questions about policies, events, and logs via semantic search."""

    def __init__(self, config: EngineConfig) -> None:
        qdrant_client = QdrantClient(host=config.qdrant_host, port=config.qdrant_port)
        vector_store = QdrantVectorStore(
            client=qdrant_client,
            collection_name=config.qdrant_collection,
        )
        embed_model = OpenAIEmbedding(
            model=config.embedding_model,
            api_key=config.openai_api_key,
        )
        llm = OpenAI(model=config.llm_model, api_key=config.openai_api_key)

        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=embed_model,
        )
        self._engine = index.as_query_engine(
            similarity_top_k=5,
            response_mode="tree_summarize",
            llm=llm,
        )

    async def query(self, question: str) -> MemoryQueryResult:
        """Execute a semantic search query against the Qdrant vector index."""
        try:
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._engine.query(question)
                ),
                timeout=30,
            )
        except asyncio.TimeoutError:
            return MemoryQueryResult(
                summary="Query timed out after 30 seconds.",
                confidence=0.0,
            )
        except Exception as exc:
            log.error("MemoryEngine query failed: %s", exc)
            return MemoryQueryResult(
                summary=f"Query failed: {exc}",
                confidence=0.0,
            )

        source_nodes = getattr(response, "source_nodes", []) or []

        sources: list[str] = []
        scores: list[float] = []
        facts: list[str] = []

        for node in source_nodes:
            score = node.score or 0.0
            scores.append(score)
            meta = node.metadata or {}
            name = meta.get("file_name") or meta.get("pipeline_name") or meta.get("collection", "unknown")
            sources.append(name)
            snippet = node.get_content()[:200].strip().replace("\n", " ")
            if snippet:
                facts.append(snippet)

        confidence = round(sum(scores) / len(scores), 4) if scores else 0.0

        return MemoryQueryResult(
            summary=response.response or "",
            sources=list(dict.fromkeys(sources)),  # deduplicate preserving order
            confidence=min(confidence, 1.0),
            relevant_facts=facts[:5],
        )
