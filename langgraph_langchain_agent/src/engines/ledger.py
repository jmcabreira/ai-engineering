"""Ledger Engine — Text-to-SQL query engine backed by PostgreSQL."""
import asyncio
import logging

from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.llms.openai import OpenAI
from sqlalchemy import create_engine, text

from src.engines.config import EngineConfig
from src.schemas.query import LedgerQueryResult

log = logging.getLogger(__name__)

_TABLE_DESCRIPTIONS = {
    "customers": (
        "Customer records with name, email, subscription plan (free/pro/enterprise), "
        "and company. Use for questions about customer counts, segments, plans."
    ),
    "orders": (
        "Order transactions with amount in BRL, quantity, status "
        "(pending/completed/failed/refunded), and timestamps. "
        "Use for revenue, sales volume, order status questions."
    ),
    "products": (
        "Product catalog with name, category, price, and SKU. "
        "Use for product-related questions."
    ),
}

_TABLES = list(_TABLE_DESCRIPTIONS.keys())


class LedgerEngine:
    """Answers factual/numerical questions by generating and executing SQL."""

    def __init__(self, config: EngineConfig) -> None:
        engine = create_engine(config.postgres_connection_string)
        sql_database = SQLDatabase(engine, include_tables=_TABLES)
        llm = OpenAI(model=config.llm_model, api_key=config.openai_api_key)
        self._engine = NLSQLTableQueryEngine(
            sql_database=sql_database,
            tables=_TABLES,
            llm=llm,
            synthesize_response=True,
            table_retrieval_kwargs={"table_context_dict": _TABLE_DESCRIPTIONS},
        )

    async def query(self, question: str) -> LedgerQueryResult:
        """Execute a natural language query against PostgreSQL via Text-to-SQL."""
        try:
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._engine.query(question)
                ),
                timeout=30,
            )
        except asyncio.TimeoutError:
            return LedgerQueryResult(
                sql_query_executed="-- timeout",
                summary="Query timed out after 30 seconds.",
                row_count=0,
            )
        except Exception as exc:
            log.error("LedgerEngine query failed: %s", exc)
            return LedgerQueryResult(
                sql_query_executed="-- error",
                summary=f"Query failed: {exc}",
                row_count=0,
            )

        sql = (response.metadata or {}).get("sql_query", "-- not captured")
        raw = response.response or ""

        # Best-effort row count from response metadata
        row_count = len((response.metadata or {}).get("result", [])) if response.metadata else 0

        # Extract data points from result rows
        data_points: list[dict] = []
        result_rows = (response.metadata or {}).get("result", [])
        col_keys = (response.metadata or {}).get("col_keys", [])
        for row in result_rows[:20]:
            if col_keys and len(col_keys) == len(row):
                data_points.append(dict(zip(col_keys, row)))
            else:
                data_points.append({"value": str(row)})

        return LedgerQueryResult(
            sql_query_executed=sql,
            summary=raw,
            row_count=row_count,
            data_points=data_points,
        )
