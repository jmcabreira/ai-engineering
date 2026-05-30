"""Router Engine — orchestrates Ledger, Memory, and Brain engines in parallel."""
import asyncio
import json
import logging
import re
import time
from typing import Any

from llama_index.llms.openai import OpenAI

from src.engines.brain import BrainEngine
from src.engines.config import EngineConfig
from src.engines.ledger import LedgerEngine
from src.engines.memory import MemoryEngine
from src.schemas.api import SourceDetail
from src.schemas.query import (
    BrainQueryResult,
    LedgerQueryResult,
    MemoryQueryResult,
    SynthesizedResponse,
)

log = logging.getLogger(__name__)

_ROUTER_SYSTEM = """You are a query router for a DataOps Knowledge Hub with 3 data stores:

1. LEDGER (PostgreSQL) — Contains: customers, orders, products tables.
   Use for: numerical questions, counts, aggregations, revenue, top-N, filtering by status/plan/date.
   Examples: "How many enterprise customers?", "Total revenue this month?", "Top 5 customers by spend"

2. MEMORY (Qdrant Vector Store) — Contains: data retention policies, SLA definitions, incident runbooks, data dictionaries, pipeline event logs, user activity logs.
   Use for: policy questions, procedure questions, "what happened" questions, historical events, definitions.
   Examples: "What is the retention policy for PII?", "What's the SLA for etl_billing_daily?", "What happened in the last failure?"

3. BRAIN (Neo4j Graph) — Contains: pipelines, tables, dashboards, teams, and their relationships (OWNS, READS_FROM, WRITES_TO, FEEDS, USED_BY).
   Use for: relationship questions, dependency/lineage questions, ownership, impact analysis.
   Examples: "Who owns the billing pipeline?", "What's impacted if orders table goes down?", "Show lineage of fact_revenue"

Given a user question, respond with a JSON object:
{"sub_questions": [{"engine": "ledger|memory|brain", "question": "the sub-question for this engine"}]}

Rules:
- Simple questions that clearly belong to one engine: return 1 sub-question.
- Complex questions that span multiple domains: decompose into 2-3 sub-questions, one per relevant engine.
- Never route to more than 3 sub-questions.
- Rephrase each sub-question to be self-contained and specific to that engine's data.
- Return ONLY the JSON object, no explanation."""

_SYNTHESIS_SYSTEM = """You are a senior data analyst synthesizing results from multiple data sources.
Given the original question and the results from each engine, write a comprehensive answer.
Be specific, cite numbers and names when available. End with a concrete recommendation if applicable.
Separate the recommendation from the main answer with the label "Recommendation:" on its own line."""


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, stripping markdown fences."""
    text = re.sub(r"```[a-z]*\n?", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


class RouterEngine:
    """Orchestrates the three query engines to answer cross-domain questions."""

    def __init__(self, config: EngineConfig) -> None:
        self._llm = OpenAI(model=config.llm_model, api_key=config.openai_api_key)
        self.ledger = LedgerEngine(config)
        self.memory = MemoryEngine(config)
        self.brain = BrainEngine(config)

    # ── Classification ────────────────────────────────────────────────────────

    async def _classify(self, question: str) -> list[dict]:
        """Ask the LLM to decompose the question into engine-specific sub-questions."""
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._llm.complete(f"{_ROUTER_SYSTEM}\n\nQuestion: {question}"),
        )
        try:
            parsed = _extract_json(response.text)
            sub_questions = parsed.get("sub_questions", [])
            # Validate structure
            valid = [
                sq for sq in sub_questions
                if isinstance(sq, dict) and sq.get("engine") in ("ledger", "memory", "brain") and sq.get("question")
            ]
            if not valid:
                raise ValueError("No valid sub-questions parsed")
            return valid[:3]
        except Exception as exc:
            log.warning("Classification failed (%s) — falling back to memory", exc)
            return [{"engine": "memory", "question": question}]

    # ── Engine execution ──────────────────────────────────────────────────────

    async def _run_engine(
        self, engine_name: str, question: str
    ) -> tuple[str, Any, Exception | None]:
        """Run a single engine query, returning (name, result, error)."""
        try:
            if engine_name == "ledger":
                result = await self.ledger.query(question)
            elif engine_name == "memory":
                result = await self.memory.query(question)
            elif engine_name == "brain":
                result = await self.brain.query(question)
            else:
                raise ValueError(f"Unknown engine: {engine_name}")
            return engine_name, result, None
        except Exception as exc:
            log.error("Engine '%s' failed: %s", engine_name, exc)
            return engine_name, None, exc

    # ── Source detail builder ─────────────────────────────────────────────────

    def _build_source_detail(self, engine_name: str, result: Any) -> SourceDetail:
        if engine_name == "ledger" and isinstance(result, LedgerQueryResult):
            return SourceDetail(
                source="ledger",
                data_store="postgresql",
                query_used=result.sql_query_executed,
                result_summary=result.summary,
                confidence=0.9,
            )
        elif engine_name == "memory" and isinstance(result, MemoryQueryResult):
            return SourceDetail(
                source="memory",
                data_store="qdrant",
                query_used="Vector search (top_k=5)",
                result_summary=result.summary,
                confidence=result.confidence,
            )
        elif engine_name == "brain" and isinstance(result, BrainQueryResult):
            return SourceDetail(
                source="brain",
                data_store="neo4j",
                query_used=result.cypher_query_executed,
                result_summary=result.summary,
                confidence=0.85,
            )
        # Fallback for errors
        return SourceDetail(
            source=engine_name,
            data_store="unknown",
            query_used="-- failed",
            result_summary=f"Engine unavailable: {result}",
            confidence=0.0,
        )

    # ── Synthesis ─────────────────────────────────────────────────────────────

    async def _synthesize(
        self,
        question: str,
        engine_results: list[tuple[str, Any, Exception | None]],
    ) -> tuple[str, str | None]:
        """Synthesize all engine results into a final answer + optional recommendation."""
        parts = []
        for name, result, err in engine_results:
            if err:
                parts.append(f"[{name.upper()}] Unavailable: {err}")
            elif result:
                summary = getattr(result, "summary", str(result))
                parts.append(f"[{name.upper()}]\n{summary}")

        formatted = "\n\n".join(parts)
        prompt = (
            f"{_SYNTHESIS_SYSTEM}\n\n"
            f"Original question: {question}\n\n"
            f"Results:\n{formatted}\n\n"
            f"Answer:"
        )
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._llm.complete(prompt)
        )
        text = response.text.strip()

        # Split recommendation if present
        recommendation = None
        if "Recommendation:" in text:
            parts_split = text.split("Recommendation:", 1)
            answer = parts_split[0].strip()
            recommendation = parts_split[1].strip()
        else:
            answer = text

        return answer, recommendation

    # ── Main query interface ──────────────────────────────────────────────────

    async def query(
        self,
        question: str,
        sources: list[str] | None = None,
    ) -> tuple[SynthesizedResponse, list[SourceDetail]]:
        """Route a question to the appropriate engines and synthesize the response.

        Args:
            question: Natural language question.
            sources: Optional filter — restrict to these engine names only.

        Returns:
            Tuple of (SynthesizedResponse, list[SourceDetail]).
        """
        start = time.monotonic()

        # Determine sub-questions
        if sources:
            sub_questions = [{"engine": s, "question": question} for s in sources if s in ("ledger", "memory", "brain")]
            log.info("Forced routing to: %s", sources)
        else:
            sub_questions = await self._classify(question)
            log.info("Classified into %d sub-question(s): %s", len(sub_questions), sub_questions)

        # Execute all engines in parallel
        tasks = [self._run_engine(sq["engine"], sq["question"]) for sq in sub_questions]
        engine_results: list[tuple[str, Any, Exception | None]] = await asyncio.gather(*tasks)

        # Synthesize
        if len(engine_results) == 1 and engine_results[0][2] is None:
            # Single engine, no errors — skip synthesis LLM call
            name, result, _ = engine_results[0]
            answer = getattr(result, "summary", str(result))
            recommendation = None
        else:
            answer, recommendation = await self._synthesize(question, engine_results)

        elapsed_ms = (time.monotonic() - start) * 1000

        # Build source details (skip failed engines)
        source_details = [
            self._build_source_detail(name, result)
            for name, result, err in engine_results
        ]

        # Confidence: weighted average of available sources
        valid_confidences = [sd.confidence for sd in source_details if sd.confidence > 0]
        confidence = round(sum(valid_confidences) / len(valid_confidences), 4) if valid_confidences else 0.0

        synthesized = SynthesizedResponse(
            answer=answer,
            sub_questions=[sq["question"] for sq in sub_questions],
            sources_consulted=[name for name, _, _ in engine_results],
            confidence=min(confidence, 1.0),
            recommendation=recommendation,
        )

        log.info(
            "RouterEngine completed in %.0fms — engines: %s",
            elapsed_ms,
            [name for name, _, _ in engine_results],
        )

        return synthesized, source_details

    async def close(self) -> None:
        await self.brain.close()
