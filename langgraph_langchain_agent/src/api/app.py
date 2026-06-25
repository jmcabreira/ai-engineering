"""FastAPI application factory."""
import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.engines.config import EngineConfig
from src.engines.router import RouterEngine

log = logging.getLogger(__name__)

_START_TIME = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = EngineConfig()
    app.state.router = RouterEngine(config)
    app.state.config = config
    log.info("RouterEngine initialized — all engines ready")
    yield
    await app.state.router.close()
    log.info("RouterEngine closed")


def create_app() -> FastAPI:
    app = FastAPI(
        title="DataOps Knowledge Hub",
        version="1.0.0",
        description=(
            "Enterprise RAG system that routes natural language questions across three specialized engines: "
            "**Ledger** (PostgreSQL / Text-to-SQL), **Memory** (Qdrant / Vector Search), and "
            "**Brain** (Neo4j / Graph Cypher). Complex queries are decomposed into sub-questions "
            "and executed in parallel."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        log.info(
            "%s %s → %d (%.2fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @app.exception_handler(asyncio.TimeoutError)
    async def timeout_handler(request: Request, exc: asyncio.TimeoutError):
        return JSONResponse(status_code=504, content={"detail": "Query timed out. Please try again."})

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        log.error("Unhandled exception on %s: %s", request.url.path, exc, exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    from src.api.routes.health import router as health_router
    from src.api.routes.ingest import router as ingest_router
    from src.api.routes.query import router as query_router

    app.include_router(health_router)
    app.include_router(query_router)
    app.include_router(ingest_router)

    # Expose uptime via app state so health route can access it
    app.state.start_time = _START_TIME

    return app
