import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.database import init_db, reset_engine
import os


@pytest.fixture(autouse=True)
async def setup_test_db():
    # Use in-memory SQLite for testing
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    await reset_engine()
    await init_db()
    yield
    # Cleanup
    await reset_engine()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "vector-studio"
    assert data["environment"] == "development"


@pytest.mark.asyncio
async def test_db_health_check(client: AsyncClient):
    response = await client.get("/api/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"