"""Unit tests for Pydantic schemas — no infrastructure required."""
import pytest
from pydantic import ValidationError

from src.schemas.api import HealthResponse, QueryRequest, QueryResponse, SourceDetail
from src.schemas.domain import (
    CustomerPlan,
    DependencyChain,
    OrderStatus,
    PipelineStatus,
    Severity,
)
from src.schemas.query import (
    BrainQueryResult,
    LedgerQueryResult,
    MemoryQueryResult,
    SynthesizedResponse,
)


class TestQueryRequest:
    def test_valid_full(self):
        req = QueryRequest(
            question="How many customers?",
            sources=["ledger", "brain"],
            include_metadata=False,
        )
        assert req.question == "How many customers?"
        assert req.sources == ["ledger", "brain"]
        assert req.include_metadata is False

    def test_valid_minimal(self):
        req = QueryRequest(question="What is the SLA?")
        assert req.sources is None
        assert req.include_metadata is True

    def test_missing_question_raises(self):
        with pytest.raises(ValidationError):
            QueryRequest()


class TestSourceDetail:
    def test_confidence_above_one_rejected(self):
        with pytest.raises(ValidationError):
            SourceDetail(
                source="ledger",
                data_store="postgresql",
                query_used="SELECT 1",
                result_summary="ok",
                confidence=1.5,
            )

    def test_confidence_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            SourceDetail(
                source="ledger",
                data_store="postgresql",
                query_used="SELECT 1",
                result_summary="ok",
                confidence=-0.1,
            )

    def test_valid_confidence_bounds(self):
        for val in (0.0, 0.5, 1.0):
            sd = SourceDetail(
                source="memory",
                data_store="qdrant",
                query_used="vector search",
                result_summary="found docs",
                confidence=val,
            )
            assert sd.confidence == val


class TestEnums:
    def test_customer_plan_values(self):
        assert CustomerPlan.FREE == "free"
        assert CustomerPlan.PRO == "pro"
        assert CustomerPlan.ENTERPRISE == "enterprise"

    def test_order_status_values(self):
        assert OrderStatus.PENDING == "pending"
        assert OrderStatus.COMPLETED == "completed"
        assert OrderStatus.FAILED == "failed"
        assert OrderStatus.REFUNDED == "refunded"

    def test_pipeline_status_values(self):
        assert PipelineStatus.COMPLETED == "completed"
        assert PipelineStatus.FAILED == "failed"
        assert PipelineStatus.WARNING == "warning"

    def test_severity_values(self):
        assert Severity.INFO == "info"
        assert Severity.WARNING == "warning"
        assert Severity.CRITICAL == "critical"

    def test_invalid_enum_raises(self):
        with pytest.raises(ValidationError):
            from src.schemas.domain import Customer
            from datetime import datetime
            Customer(
                id=1, name="Test", email="t@t.com",
                plan="invalid_plan",
                created_at=datetime.now(),
            )


class TestDependencyChain:
    def test_empty_lists_valid(self):
        dc = DependencyChain(source="etl_billing_daily")
        assert dc.downstream_pipelines == []
        assert dc.downstream_tables == []
        assert dc.downstream_dashboards == []
        assert dc.impacted_teams == []

    def test_populated(self):
        dc = DependencyChain(
            source="orders",
            downstream_pipelines=["etl_billing_daily"],
            impacted_teams=["team-billing"],
        )
        assert len(dc.downstream_pipelines) == 1
        assert len(dc.impacted_teams) == 1


class TestQueryResultModels:
    def test_ledger_result(self):
        r = LedgerQueryResult(
            sql_query_executed="SELECT count(*) FROM customers",
            summary="There are 100 customers.",
            row_count=1,
            data_points=[{"count": 100}],
        )
        assert r.row_count == 1

    def test_memory_result_confidence_clamped(self):
        with pytest.raises(ValidationError):
            MemoryQueryResult(summary="ok", confidence=2.0)

    def test_brain_result_with_dependency_chain(self):
        r = BrainQueryResult(
            cypher_query_executed="MATCH (n) RETURN n",
            summary="Found 3 pipelines.",
            nodes_traversed=3,
            dependency_chain=DependencyChain(
                source="orders",
                downstream_pipelines=["etl_billing_daily"],
            ),
        )
        assert r.dependency_chain.source == "orders"

    def test_synthesized_response(self):
        r = SynthesizedResponse(
            answer="Enterprise customers: 42.",
            sub_questions=["How many enterprise customers?"],
            sources_consulted=["ledger"],
            confidence=0.9,
        )
        assert r.recommendation is None
        assert r.confidence == 0.9


class TestHealthResponse:
    def test_arbitrary_service_names(self):
        h = HealthResponse(
            status="healthy",
            services={"postgres": "healthy", "custom-db": "degraded"},
            uptime_seconds=120.5,
            version="1.0.0",
        )
        assert h.services["custom-db"] == "degraded"
