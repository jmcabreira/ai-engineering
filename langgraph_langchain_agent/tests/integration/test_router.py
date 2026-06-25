"""Integration tests for RouterEngine — requires full stack + valid OPENAI_API_KEY."""
import pytest

from src.engines.router import RouterEngine
from src.schemas.query import SynthesizedResponse


@pytest.mark.integration
class TestRouterEngine:
    async def test_single_engine_routing(self, config):
        router = RouterEngine(config)
        response, sources = await router.query("How many enterprise customers do we have?")
        assert isinstance(response, SynthesizedResponse)
        assert len(sources) >= 1
        assert any(s.source == "ledger" for s in sources)
        assert response.answer
        await router.close()

    async def test_multi_engine_routing(self, config):
        router = RouterEngine(config)
        response, sources = await router.query(
            "What are the top customers by revenue, what is the SLA for the billing pipeline, "
            "and what systems depend on the orders table?"
        )
        assert isinstance(response, SynthesizedResponse)
        assert len(sources) >= 2
        assert len(response.sub_questions) >= 2
        assert response.answer
        await router.close()

    async def test_forced_routing(self, config):
        router = RouterEngine(config)
        response, sources = await router.query(
            "Tell me about billing",
            sources=["ledger", "brain"],
        )
        assert isinstance(response, SynthesizedResponse)
        assert all(s.source in ("ledger", "brain") for s in sources)
        await router.close()

    async def test_synthesized_response_fields(self, config):
        router = RouterEngine(config)
        response, sources = await router.query("How many products do we sell?")
        assert isinstance(response, SynthesizedResponse)
        assert 0.0 <= response.confidence <= 1.0
        assert isinstance(response.sources_consulted, list)
        assert isinstance(response.sub_questions, list)
        await router.close()

    async def test_wow_moment(self, config):
        """Cross-domain query hitting all 3 engines simultaneously."""
        router = RouterEngine(config)
        response, sources = await router.query(
            "Summarize the top customers by spend, what are their data retention requirements, "
            "and what systems would be impacted if the orders table went down?"
        )
        assert isinstance(response, SynthesizedResponse)
        assert len(sources) >= 2
        assert response.answer
        await router.close()
