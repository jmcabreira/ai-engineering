"""Entry point for the ingestion pipeline. Run with: python -m src.ingestion.run [--limit N]"""
import argparse
import asyncio
import logging

from src.ingestion.config import IngestionConfig
from src.ingestion.pipeline import build_pipeline, run_pipeline
from src.ingestion.readers import MongoDBReader, SeaweedFSReader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main(limit: int | None = None) -> None:
    config = IngestionConfig()

    logger.info("Loading documents from SeaweedFS...")
    seaweedfs_docs = SeaweedFSReader(config).load_data()
    logger.info("  → %d documents from SeaweedFS", len(seaweedfs_docs))

    logger.info("Loading documents from MongoDB...")
    mongo_docs = MongoDBReader(config).load_data()
    logger.info("  → %d documents from MongoDB", len(mongo_docs))

    all_documents = seaweedfs_docs + mongo_docs
    if limit:
        all_documents = all_documents[:limit]
        logger.info("Limiting to %d documents for validation", limit)
    logger.info("Total documents to ingest: %d", len(all_documents))

    pipeline = build_pipeline(config)
    nodes = await run_pipeline(pipeline, all_documents)
    logger.info("Ingestion complete. %d nodes indexed in Qdrant.", len(nodes))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max documents to ingest")
    args = parser.parse_args()
    asyncio.run(main(limit=args.limit))
