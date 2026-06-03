import pytest
from dotenv import load_dotenv

load_dotenv()

from src.engines.config import EngineConfig


@pytest.fixture(scope="session")
def config():
    """Load config from .env (must have valid OPENAI_API_KEY for integration tests)."""
    return EngineConfig()
