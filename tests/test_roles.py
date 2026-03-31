"""
Tests for role management endpoints.
"""
import pytest


@pytest.mark.asyncio
async def test_list_roles_returns_list(client):
    resp = await client.get("/roles")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_role_success(client):
    payload = {
        "name": "Test Engineer",
        "agent_id": "main",
        "description": "A test role",
        "system_prompt": "You are a test engineer.",
        "is_controller": False,
    }
    resp = await client.post("/roles", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Engineer"
    assert data["agent_id"] == "main"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_role_missing_name(client):
    resp = await client.post("/roles", json={"agent_id": "main"})
    assert resp.status_code == 422  # Unprocessable Entity


@pytest.mark.asyncio
async def test_get_role_not_found(client):
    resp = await client.get("/roles/nonexistent-id-12345")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_role_after_create(client):
    # Create
    payload = {"name": "Architect", "agent_id": "main", "description": "", "system_prompt": ""}
    create_resp = await client.post("/roles", json=payload)
    assert create_resp.status_code == 200
    role_id = create_resp.json()["id"]

    # Get
    get_resp = await client.get(f"/roles/{role_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == role_id
    assert get_resp.json()["name"] == "Architect"


@pytest.mark.asyncio
async def test_delete_role(client):
    # Create then delete
    payload = {"name": "ToDelete", "agent_id": "main", "description": "", "system_prompt": ""}
    role_id = (await client.post("/roles", json=payload)).json()["id"]

    del_resp = await client.delete(f"/roles/{role_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["ok"] is True

    # Confirm gone
    get_resp = await client.get(f"/roles/{role_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_role_not_found(client):
    resp = await client.delete("/roles/nonexistent-id-99999")
    assert resp.status_code == 404
