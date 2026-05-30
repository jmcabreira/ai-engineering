"""Entry point for the MCP server. Run with: python -m src.mcp.run"""
import asyncio
import logging

from src.mcp.server import run_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main() -> None:
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
