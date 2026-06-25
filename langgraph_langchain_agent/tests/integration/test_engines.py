"""Integration tests for individual query engines — requires full stack running."""
import pytest

from src.engines.brain import BrainEngine
from src.engines.ledger import LedgerEngine
from src.engines.memory import MemoryEngine
from src.schemas.query import BrainQueryResult, LedgerQueryResult, MemoryQueryResult


@pytest.mark.integration
class TestLedgerEngine:
    async def test_count_query(self, config):
        engine = LedgerEngine(config)
        result = await engine.query("How many customers are there?")
        assert isinstance(result, LedgerQueryResult)
        assert "SELECT" in result.sql_query_executed.upper()
        assert result.row_count >= 0

    async def test_aggregation_query(self, config):
        engine = LedgerEngine(config)
        result = await engine.query("What is the total revenue from completed orders?")
        assert isinstance(result, LedgerQueryResult)
        assert result.summary
        assert len(result.sql_query_executed) > 0

    async def test_returns_data_points(self, config):
        engine = LedgerEngine(config)
        result = await engine.query("List the top 3 products by price")
        assert isinstance(result, LedgerQueryResult)
        assert isinstance(result.data_points, list)


@pytest.mark.integration
class TestMemoryEngine:
    async def test_policy_query(self, config):
        engine = MemoryEngine(config)
        result = await engine.query("What is the data retention policy for PII?")
        assert isinstance(result, MemoryQueryResult)
        assert result.confidence >= 0.0
        assert result.summary

    async def test_sources_populated(self, config):
        engine = MemoryEngine(config)
        result = await engine.query("What is the data retention policy for PII?")
        assert isinstance(result, MemoryQueryResult)
        assert len(result.sources) > 0

    async def test_event_log_query(self, config):
        engine = MemoryEngine(config)
        result = await engine.query("What pipeline failures happened recently?")
        assert isinstance(result, MemoryQueryResult)
        assert result.summary


@pytest.mark.integration
class TestBrainEngine:
    async def test_ownership_query(self, config):
        engine = BrainEngine(config)
        result = await engine.query("What pipelines does team-billing own?")
        assert isinstance(result, BrainQueryResult)
        assert "MATCH" in result.cypher_query_executed.upper()
        assert result.summary
        await engine.close()

    async def test_dependency_query(self, config):
        engine = BrainEngine(config)
        result = await engine.query("What would be impacted if the orders table goes down?")
        assert isinstance(result, BrainQueryResult)
        assert result.nodes_traversed >= 0
        await engine.close()

    async def test_lineage_query(self, config):
        engine = BrainEngine(config)
        result = await engine.query("Show the lineage of fact_revenue table")
        assert isinstance(result, BrainQueryResult)
        assert result.cypher_query_executed
        await engine.close()
