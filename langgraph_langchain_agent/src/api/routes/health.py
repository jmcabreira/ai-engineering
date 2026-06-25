"""GET /health — service health check."""
import asyncio
import time

import httpx
from fastapi import APIRouter, Request
from neo4j import AsyncGraphDatabase
from pymongo import MongoClient
from sqlalchemy import create_engine, text

from src.schemas.api import HealthResponse

router = APIRouter(tags=["health"])


async def _check_postgres(conn_str: str) -> str:
    def _run():
        engine = create_engine(conn_str)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()

    try:
        await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _run), timeout=5
        )
        return "healthy"
    except Exception:
        return "unhealthy"


async def _check_qdrant(host: str, port: int) -> str:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"http://{host}:{port}/healthz")
            return "healthy" if r.status_code == 200 else "degraded"
    except Exception:
        return "unhealthy"


async def _check_neo4j(uri: str, user: str, password: str) -> str:
    try:
        driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        async with asyncio.timeout(5):
            async with driver.session() as session:
                await session.run("RETURN 1")
        await driver.close()
        return "healthy"
    except Exception:
        return "unhealthy"


async def _check_mongo(host: str, port: int) -> str:
    def _run():
        client = MongoClient(host, port, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        client.close()

    try:
        await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _run), timeout=5
        )
        return "healthy"
    except Exception:
        return "unhealthy"


async def _check_seaweedfs(host: str, port: int) -> str:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"http://{host}:{port}/cluster/status")
            return "healthy" if r.status_code == 200 else "degraded"
    except Exception:
        return "unhealthy"


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check(req: Request) -> HealthResponse:
    """Check connectivity to all backend services."""
    config = req.app.state.config
    uptime = time.monotonic() - req.app.state.start_time

    pg, qd, n4j, mg, swfs = await asyncio.gather(
        _check_postgres(config.postgres_connection_string),
        _check_qdrant(config.qdrant_host, config.qdrant_port),
        _check_neo4j(config.neo4j_uri, config.neo4j_user, config.neo4j_password),
        _check_mongo(config.mongo_host, config.mongo_port),
        _check_seaweedfs(config.seaweedfs_host, config.seaweedfs_port),
    )

    services = {
        "postgres": pg,
        "qdrant": qd,
        "neo4j": n4j,
        "mongodb": mg,
        "seaweedfs": swfs,
    }

    critical = {pg, qd, n4j}
    overall = "healthy" if all(s == "healthy" for s in critical) else "degraded"

    return HealthResponse(
        status=overall,
        services=services,
        uptime_seconds=round(uptime, 2),
        version=req.app.version,
    )
