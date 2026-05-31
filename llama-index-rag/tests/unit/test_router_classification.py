"""Unit tests for RouterEngine classification logic — LLM is mocked."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.engines.router import RouterEngine, _extract_json
from src.schemas.query import SynthesizedResponse


# ── _extract_json helper ──────────────────────────────────────────────────────

class TestExtractJson:
    def test_plain_json(self):
        raw = '{"sub_questions": [{"engine": "ledger", "question": "count customers"}]}'
        result = _extract_json(raw)
        assert result["sub_questions"][0]["engine"] == "ledger"

    def test_json_with_markdown_fence(self):
        raw = "```json\n{\"sub_questions\": [{\"engine\": \"brain\", \"question\": \"who owns it\"}]}\n```"
        result = _extract_json(raw)
        assert result["sub_questions"][0]["engine"] == "brain"

    def test_json_embedded_in_text(self):
        raw = 'Here is the routing: {"sub_questions": [{"engine": "memory", "question": "SLA?"}]} done.'
        result = _extract_json(raw)
        assert result["sub_questions"][0]["engine"] == "memory"


# ── Router classify logic ─────────────────────────────────────────────────────

def _make_router() -> RouterEngine:
    """Instantiate RouterEngine without real connections by patching constructors."""
    with (
        patch("src.engines.router.LedgerEngine.__init__", return_value=None),
        patch("src.engines.router.MemoryEngine.__init__", return_value=None),
        patch("src.engines.router.BrainEngine.__init__", return_value=None),
        patch("src.engines.router.OpenAI.__init__", return_value=None),
    ):
        from src.engines.config import EngineConfig
        config = EngineConfig(openai_api_key="sk-test")
        return RouterEngine(config)


def _mock_llm_response(router: RouterEngine, json_payload: dict):
    """Patch the LLM complete call to return a fixed JSON string."""
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(json_payload)
    router._llm = MagicMock()
    router._llm.complete = MagicMock(return_value=mock_resp)


class TestRouterClassification:
    @pytest.mark.asyncio
    async def test_single_engine_ledger(self):
        router = _make_router()
        _mock_llm_response(router, {
            "sub_questions": [{"engine": "ledger", "question": "How many customers?"}]
        })
        sub_qs = await router._classify("How many customers?")
        assert len(sub_qs) == 1
        assert sub_qs[0]["engine"] == "ledger"

    @pytest.mark.asyncio
    async def test_single_engine_memory(self):
        router = _make_router()
        _mock_llm_response(router, {
            "sub_questions": [{"engine": "memory", "question": "What is the SLA?"}]
        })
        sub_qs = await router._classify("What is the SLA for etl_billing_daily?")
        assert sub_qs[0]["engine"] == "memory"

    @pytest.mark.asyncio
    async def test_single_engine_brain(self):
        router = _make_router()
        _mock_llm_response(router, {
            "sub_questions": [{"engine": "brain", "question": "Who owns the orders table?"}]
        })
        sub_qs = await router._classify("Who owns the orders table?")
        assert sub_qs[0]["engine"] == "brain"

    @pytest.mark.asyncio
    async def test_multi_engine_decomposition(self):
        router = _make_router()
        _mock_llm_response(router, {
            "sub_questions": [
                {"engine": "ledger", "question": "Top customers by revenue"},
                {"engine": "memory", "question": "What is the SLA for billing?"},
                {"engine": "brain", "question": "What depends on orders table?"},
            ]
        })
        sub_qs = await router._classify("Top customers, SLA, and orders impact?")
        assert len(sub_qs) == 3
        engines = {sq["engine"] for sq in sub_qs}
        assert engines == {"ledger", "memory", "brain"}

    @pytest.mark.asyncio
    async def test_malformed_llm_response_fallback(self):
        router = _make_router()
        mock_resp = MagicMock()
        mock_resp.text = "Sorry, I cannot determine the routing."
        router._llm = MagicMock()
        router._llm.complete = MagicMock(return_value=mock_resp)
        sub_qs = await router._classify("Some question")
        # Falls back to memory
        assert len(sub_qs) == 1
        assert sub_qs[0]["engine"] == "memory"

    @pytest.mark.asyncio
    async def test_sources_filter_bypasses_classification(self):
        router = _make_router()
        # LLM should NOT be called when sources is provided
        router._llm = MagicMock()
        router._llm.complete = MagicMock(side_effect=Exception("should not be called"))

        # Patch _run_engine to avoid real connections
        async def fake_run(name, question):
            from src.schemas.query import LedgerQueryResult
            return name, LedgerQueryResult(
                sql_query_executed="SELECT 1",
                summary="ok",
                row_count=1,
            ), None

        router._run_engine = fake_run

        # Patch _synthesize
        async def fake_synth(question, results):
            return "synthesized", None
        router._synthesize = fake_synth

        response, sources = await router.query("anything", sources=["ledger"])
        assert all(s.source == "ledger" for s in sources)
        # LLM classify was not invoked
        router._llm.complete.assert_not_called()
