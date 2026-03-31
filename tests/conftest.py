"""
Pytest configuration and shared fixtures for AI Team Platform tests.
"""
import json
import pytest
import pytest_asyncio
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# Ensure data files exist before importing app
_data_dir = Path(__file__).parent.parent / "data"
_data_dir.mkdir(exist_ok=True)
if not (_data_dir / "roles.json").exists():
    (_data_dir / "roles.json").write_text("{}")
if not (_data_dir / "tasks.json").exists():
    (_data_dir / "tasks.json").write_text("{}")

from main import app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    """Async HTTP client wired directly to the FastAPI app (no real server needed)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
