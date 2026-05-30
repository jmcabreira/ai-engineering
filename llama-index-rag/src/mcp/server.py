"""MCP server exposing the DataOps Knowledge Hub as tools for AI agents."""
import json
import logging
import os

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

log = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

server = Server("dataops-knowledge-hub")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="query_knowledge_hub",
            description=(
                "Query the DataOps Knowledge Hub — an enterprise RAG system that searches across "
                "3 data stores: PostgreSQL (factual/numerical data about customers, orders, products), "
                "Qdrant (policies, SLAs, runbooks, incident logs), and Neo4j (pipeline lineage, "
                "table dependencies, team ownership). "
                "The system automatically routes your question to the appropriate engine(s) and "
                "returns a synthesized answer with sources and recommendations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Natural language question about the data platform",
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["ledger", "memory", "brain"]},
                        "description": "Optional: restrict search to specific engines. Omit to search all.",
                    },
                },
                "required": ["question"],
            },
        ),
        Tool(
            name="check_platform_health",
            description=(
                "Check the health status of all services in the DataOps Knowledge Hub: "
                "PostgreSQL, Qdrant, Neo4j, MongoDB, and SeaweedFS. "
                "Returns the status of each service and overall platform health."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="trigger_ingestion",
            description=(
                "Trigger a re-ingestion of all data sources (SeaweedFS documents + MongoDB logs) "
                "into the Memory engine (Qdrant). Use this after new documents have been added "
                "or when you want to refresh the search index."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        if name == "query_knowledge_hub":
            return await _query_knowledge_hub(client, arguments)
        elif name == "check_platform_health":
            return await _check_platform_health(client)
        elif name == "trigger_ingestion":
            return await _trigger_ingestion(client)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _query_knowledge_hub(client: httpx.AsyncClient, arguments: dict) -> list[TextContent]:
    try:
        response = await client.post(
            f"{API_BASE_URL}/api/v1/query",
            json={
                "question": arguments["question"],
                "sources": arguments.get("sources"),
                "include_metadata": True,
            },
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        return [TextContent(type="text", text=f"Error calling Knowledge Hub API: {exc}")]

    text = f"## Answer\n\n{data['answer']}\n\n"

    if data.get("recommendation"):
        text += f"## Recommendation\n\n{data['recommendation']}\n\n"

    if data.get("sub_questions"):
        text += "## How the question was decomposed\n\n"
        for i, sq in enumerate(data["sub_questions"], 1):
            text += f"{i}. {sq}\n"
        text += "\n"

    if data.get("sources_consulted"):
        text += "## Sources Consulted\n\n"
        for source in data["sources_consulted"]:
            text += f"- **{source['source']}** ({source['data_store']}): {source['result_summary']}\n"
            text += f"  Query: `{source['query_used']}`\n"
        text += "\n"

    text += f"_Processing time: {data.get('processing_time_ms', 0):.0f}ms_"
    return [TextContent(type="text", text=text)]


async def _check_platform_health(client: httpx.AsyncClient) -> list[TextContent]:
    try:
        response = await client.get(f"{API_BASE_URL}/health")
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        return [TextContent(type="text", text=f"Error reaching health endpoint: {exc}")]

    overall = data.get("status", "unknown").upper()
    text = f"## Platform Health: {overall}\n\n"
    text += f"Uptime: {data.get('uptime_seconds', 0):.0f}s | Version: {data.get('version', 'unknown')}\n\n"
    text += "### Services\n\n"
    for svc, status in data.get("services", {}).items():
        icon = "✅" if status == "healthy" else ("⚠️" if status == "degraded" else "❌")
        text += f"{icon} **{svc}**: {status}\n"
    return [TextContent(type="text", text=text)]


async def _trigger_ingestion(client: httpx.AsyncClient) -> list[TextContent]:
    try:
        response = await client.post(f"{API_BASE_URL}/api/v1/ingest")
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        return [TextContent(type="text", text=f"Error triggering ingestion: {exc}")]

    text = (
        f"## Ingestion Triggered\n\n"
        f"**Status:** {data.get('status', 'unknown')}\n"
        f"**Job ID:** `{data.get('job_id', 'unknown')}`\n\n"
        f"{data.get('message', '')}"
    )
    return [TextContent(type="text", text=text)]


async def run_server() -> None:
    log.info("DataOps Knowledge Hub MCP server starting (API: %s)", API_BASE_URL)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
