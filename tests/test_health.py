"""
Tests for GET /health endpoint.
"""
import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_response_schema(client):
    resp = await client.get("/health")
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], float)


@pytest.mark.asyncio
async def test_health_includes_counts(client):
    resp = await client.get("/health")
    data = resp.json()
    assert "roles" in data
    assert "tasks" in data
    assert isinstance(data["roles"], int)
    assert isinstance(data["tasks"], int)
