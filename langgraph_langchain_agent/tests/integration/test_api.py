"""Integration tests for FastAPI endpoints — requires server running on localhost:8000."""
import pytest
import httpx

BASE_URL = "http://localhost:8000"


@pytest.mark.integration
class TestHealthEndpoint:
    async def test_returns_200(self):
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{BASE_URL}/health")
        assert r.status_code == 200

    async def test_response_shape(self):
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{BASE_URL}/health")
        data = r.json()
        assert data["status"] in ("healthy", "degraded")
        assert "services" in data
        assert "uptime_seconds" in data
        assert "version" in data

    async def test_all_services_present(self):
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{BASE_URL}/health")
        services = r.json()["services"]
        for svc in ("postgres", "qdrant", "neo4j", "mongodb", "seaweedfs"):
            assert svc in services


@pytest.mark.integration
class TestQueryEndpoint:
    async def test_basic_query(self):
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{BASE_URL}/api/v1/query",
                json={"question": "How many customers do we have?"},
            )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "sources_consulted" in data
        assert data["processing_time_ms"] > 0

    async def test_response_includes_metadata(self):
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{BASE_URL}/api/v1/query",
                json={"question": "How many customers do we have?", "include_metadata": True},
            )
        data = r.json()
        assert isinstance(data["sub_questions"], list)
        assert isinstance(data["sources_consulted"], list)
        for sd in data["sources_consulted"]:
            assert "source" in sd
            assert "data_store" in sd
            assert "query_used" in sd
            assert "confidence" in sd

    async def test_sources_filter(self):
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{BASE_URL}/api/v1/query",
                json={"question": "Who owns the billing pipeline?", "sources": ["brain"]},
            )
        assert r.status_code == 200
        data = r.json()
        assert all(s["source"] == "brain" for s in data["sources_consulted"])

    async def test_invalid_request_returns_422(self):
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{BASE_URL}/api/v1/query",
                json={"wrong_field": "test"},
            )
        assert r.status_code == 422

    async def test_question_echoed_in_response(self):
        question = "How many enterprise customers?"
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{BASE_URL}/api/v1/query",
                json={"question": question},
            )
        assert r.json()["question"] == question


@pytest.mark.integration
class TestIngestEndpoint:
    async def test_returns_immediately(self):
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(f"{BASE_URL}/api/v1/ingest")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ingestion_started"
        assert "job_id" in data
