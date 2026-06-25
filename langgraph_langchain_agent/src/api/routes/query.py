"""POST /api/v1/query — main Knowledge Hub query endpoint."""
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.schemas.api import QueryRequest, QueryResponse

router = APIRouter(prefix="/api/v1", tags=["query"])


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Query the DataOps Knowledge Hub",
)
async def query_knowledge_hub(request: QueryRequest, req: Request) -> QueryResponse:
    """
    Route a natural language question to the appropriate engine(s).

    - **Ledger** (PostgreSQL): counts, revenue, orders, customer segments
    - **Memory** (Qdrant): policies, SLAs, runbooks, pipeline event history
    - **Brain** (Neo4j): ownership, lineage, dependency impact analysis

    Complex questions are decomposed into sub-questions and executed in **parallel**.
    """
    start = time.perf_counter()

    synthesized, source_details = await req.app.state.router.query(
        question=request.question,
        sources=request.sources,
    )

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    return QueryResponse(
        question=request.question,
        answer=synthesized.answer,
        sub_questions=synthesized.sub_questions,
        sources_consulted=source_details if request.include_metadata else [],
        recommendation=synthesized.recommendation,
        processing_time_ms=elapsed_ms,
    )
