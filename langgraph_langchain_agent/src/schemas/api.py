from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request body for POST /query."""

    question: str = Field(
        description="The natural language question to ask the Knowledge Hub",
        json_schema_extra={"examples": ["How many enterprise customers do we have?"]},
    )
    sources: Optional[list[str]] = Field(
        None,
        description="Optionally restrict to specific sources: 'ledger', 'memory', 'brain'. None = all.",
        json_schema_extra={"examples": [None, ["ledger"], ["memory", "brain"]]},
    )
    include_metadata: bool = Field(
        default=True,
        description="Whether to include sub-questions, SQL/Cypher queries, and source details",
    )


class SourceDetail(BaseModel):
    """Details about a specific source that was consulted."""

    source: str = Field(description="Engine name: ledger, memory, or brain")
    data_store: str = Field(description="Underlying store: postgresql, qdrant, or neo4j")
    query_used: str = Field(description="The actual query executed (SQL, vector search, or Cypher)")
    result_summary: str = Field(description="Summary of what this source returned")
    confidence: float = Field(ge=0.0, le=1.0)


class QueryResponse(BaseModel):
    """Response body for POST /query."""

    question: str = Field(description="The original question")
    answer: str = Field(description="Synthesized answer combining all sources")
    sub_questions: list[str] = Field(
        default_factory=list, description="How the question was decomposed"
    )
    sources_consulted: list[SourceDetail] = Field(description="Details per source")
    recommendation: Optional[str] = Field(None, description="Actionable recommendation")
    processing_time_ms: float = Field(description="Total processing time in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str = Field(default="healthy")
    services: dict[str, str] = Field(
        description="Health status per service: postgres, qdrant, neo4j, mongodb, seaweedfs"
    )
    uptime_seconds: float
    version: str
