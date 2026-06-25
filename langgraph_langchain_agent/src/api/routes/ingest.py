"""POST /api/v1/ingest — on-demand re-ingestion trigger."""
import asyncio
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Request

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["ingestion"])


async def _run_ingestion(config) -> None:
    from src.ingestion.pipeline import build_pipeline, run_pipeline
    from src.ingestion.readers import MongoDBReader, SeaweedFSReader

    from src.ingestion.config import IngestionConfig

    ing_config = IngestionConfig(
        openai_api_key=config.openai_api_key,
        llm_model=config.llm_model,
        embedding_model=config.embedding_model,
        qdrant_host=config.qdrant_host,
        qdrant_port=config.qdrant_port,
        qdrant_collection=config.qdrant_collection,
        seaweedfs_host=config.seaweedfs_host,
        seaweedfs_port=config.seaweedfs_port,
        mongo_host=config.mongo_host,
        mongo_port=config.mongo_port,
        mongo_db=config.mongo_db,
    )

    seaweedfs_docs = SeaweedFSReader(ing_config).load_data()
    mongo_docs = MongoDBReader(ing_config).load_data()
    all_docs = seaweedfs_docs + mongo_docs
    log.info("Background ingestion: %d documents loaded", len(all_docs))

    pipeline = build_pipeline(ing_config)
    nodes = await run_pipeline(pipeline, all_docs)
    log.info("Background ingestion complete: %d nodes indexed", len(nodes))


@router.post("/ingest", summary="Trigger re-ingestion")
async def trigger_ingestion(background_tasks: BackgroundTasks, req: Request) -> dict:
    """
    Trigger a background re-ingestion of all data sources into the Memory engine.

    Returns immediately with a job ID. Monitor progress via server logs.
    """
    job_id = str(uuid.uuid4())[:8]
    config = req.app.state.config
    background_tasks.add_task(_run_ingestion, config)
    log.info("Ingestion job %s started in background", job_id)
    return {
        "status": "ingestion_started",
        "job_id": job_id,
        "message": "Ingestion running in background. Check server logs for progress.",
    }
