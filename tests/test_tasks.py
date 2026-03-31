"""
Tests for task endpoints.
"""
import pytest


@pytest.mark.asyncio
async def test_list_tasks_returns_list(client):
    resp = await client.get("/tasks")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_task_not_found(client):
    resp = await client.get("/tasks/nonexistent-task-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_sub_task_not_found(client):
    resp = await client.get("/tasks/nonexistent-task/sub/nonexistent-role")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_controller_returns_role_or_null(client):
    resp = await client.get("/controller")
    assert resp.status_code == 200
    # Either a role object or null
    data = resp.json()
    assert data is None or isinstance(data, dict)
