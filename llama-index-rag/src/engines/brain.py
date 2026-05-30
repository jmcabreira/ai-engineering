"""Brain Engine — Graph traversal query engine backed by Neo4j."""
import asyncio
import logging
import re
from typing import Any

from llama_index.llms.openai import OpenAI
from neo4j import AsyncGraphDatabase

from src.engines.config import EngineConfig
from src.schemas.domain import DependencyChain
from src.schemas.query import BrainQueryResult

log = logging.getLogger(__name__)

_GRAPH_SCHEMA = """
Graph schema:
  Nodes: Team (name), Pipeline (name, schedule, sla_minutes, owner),
         Table (name, schema, database), Dashboard (name, owner)
  Relationships:
    (Team)-[:OWNS]->(Pipeline)
    (Team)-[:OWNS]->(Table)
    (Pipeline)-[:READS_FROM]->(Table)
    (Pipeline)-[:WRITES_TO]->(Table)
    (Pipeline)-[:FEEDS]->(Pipeline)
    (Dashboard)-[:USED_BY]->(Team)

Example Cypher queries:
  "What pipelines does team-billing own?"
    → MATCH (t:Team {name:'team-billing'})-[:OWNS]->(p:Pipeline) RETURN p.name AS pipeline
  "What would be impacted if the orders table goes down?"
    → MATCH (tbl:Table {name:'orders'})<-[:READS_FROM|WRITES_TO*1..3]-(downstream) RETURN downstream
  "Show lineage of fact_revenue"
    → MATCH path=(source)-[:READS_FROM|WRITES_TO|FEEDS*]->(t:Table {name:'fact_revenue'}) RETURN path
  "Who owns the customers table?"
    → MATCH (team:Team)-[:OWNS]->(t:Table {name:'customers'}) RETURN team.name AS owner
"""

_CYPHER_SYSTEM = f"""You are a Neo4j Cypher expert. Given a natural language question,
generate a single valid Cypher query that answers the question using the schema below.
Return ONLY the Cypher query, no explanation, no markdown fences.

{_GRAPH_SCHEMA}"""

_SYNTHESIS_SYSTEM = """You are a data expert. Summarize graph query results in clear natural language.
Be concise and specific. If results are empty, say what the query checked and that nothing was found."""


def _extract_cypher(text: str) -> str:
    """Strip markdown fences and whitespace from LLM Cypher output."""
    text = re.sub(r"```[a-z]*\n?", "", text).strip()
    return text.split(";")[0].strip()


def _parse_dependency_chain(question: str, records: list[dict]) -> DependencyChain | None:
    """Build a DependencyChain if the question involves impact/dependency analysis."""
    keywords = ("impact", "downstream", "depend", "goes down", "affect", "lineage")
    if not any(k in question.lower() for k in keywords):
        return None

    source = ""
    pipelines, tables, dashboards, teams = [], [], [], []
    for record in records:
        for value in record.values():
            if isinstance(value, dict):
                labels = value.get("labels", [])
                props = value.get("properties", {})
                name = props.get("name", "")
                if not name:
                    continue
                if "Pipeline" in labels:
                    pipelines.append(name)
                elif "Table" in labels:
                    if not source:
                        source = name
                    else:
                        tables.append(name)
                elif "Dashboard" in labels:
                    dashboards.append(name)
                elif "Team" in labels:
                    teams.append(name)
            elif isinstance(value, str) and value:
                if not source:
                    source = value

    if not source and not pipelines and not tables:
        return None

    return DependencyChain(
        source=source or "unknown",
        downstream_pipelines=list(set(pipelines)),
        downstream_tables=list(set(tables)),
        downstream_dashboards=list(set(dashboards)),
        impacted_teams=list(set(teams)),
    )


class BrainEngine:
    """Answers relationship/lineage questions via LLM-generated Cypher on Neo4j."""

    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._llm = OpenAI(model=config.llm_model, api_key=config.openai_api_key)
        self._driver = AsyncGraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
        )

    async def _generate_cypher(self, question: str) -> str:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._llm.complete(
                f"{_CYPHER_SYSTEM}\n\nQuestion: {question}"
            ),
        )
        return _extract_cypher(response.text)

    async def _run_cypher(self, cypher: str) -> list[dict]:
        async with self._driver.session() as session:
            result = await session.run(cypher)
            records = await result.data()
            return records

    async def _synthesize(self, question: str, cypher: str, records: list[dict]) -> str:
        prompt = (
            f"{_SYNTHESIS_SYSTEM}\n\n"
            f"Question: {question}\n"
            f"Cypher executed: {cypher}\n"
            f"Results ({len(records)} records): {records[:10]}\n\n"
            f"Summary:"
        )
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._llm.complete(prompt)
        )
        return response.text.strip()

    async def query(self, question: str) -> BrainQueryResult:
        """Generate Cypher, execute against Neo4j, synthesize result."""
        cypher = ""
        records: list[dict] = []
        try:
            async with asyncio.timeout(30):
                cypher = await self._generate_cypher(question)
                log.info("BrainEngine Cypher: %s", cypher)
                records = await self._run_cypher(cypher)
        except asyncio.TimeoutError:
            return BrainQueryResult(
                cypher_query_executed=cypher or "-- timeout",
                summary="Query timed out after 30 seconds.",
                nodes_traversed=0,
            )
        except Exception as exc:
            log.error("BrainEngine query failed: %s", exc)
            return BrainQueryResult(
                cypher_query_executed=cypher or "-- error",
                summary=f"Query failed: {exc}",
                nodes_traversed=0,
            )

        summary = await self._synthesize(question, cypher, records)

        # Extract relationship strings from record keys
        relationships: list[str] = []
        for record in records:
            for k, v in record.items():
                if isinstance(v, str):
                    relationships.append(f"{k}: {v}")
                elif isinstance(v, dict) and v.get("properties", {}).get("name"):
                    relationships.append(v["properties"]["name"])
        relationships = list(dict.fromkeys(relationships))[:10]

        dep_chain = _parse_dependency_chain(question, records)

        return BrainQueryResult(
            cypher_query_executed=cypher,
            summary=summary,
            nodes_traversed=len(records),
            relationships_found=relationships,
            dependency_chain=dep_chain,
        )

    async def close(self) -> None:
        await self._driver.close()
