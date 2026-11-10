import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.database import init_db, reset_engine
from app.models import Exercise, ExerciseCategory
import os


@pytest.fixture(autouse=True)
async def setup_test_db():
    # Use in-memory SQLite for testing with shared cache
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:?cache=shared"
    settings.database_url = "sqlite+aiosqlite:///:memory:?cache=shared"
    await reset_engine()
    await init_db()
    yield
    # Cleanup
    await reset_engine()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def sample_exercise(client: AsyncClient):
    """Create a sample exercise for testing routines."""
    # We need to create an exercise first
    from app.core.database import get_session
    from app.models import Exercise, ExerciseCategory
    
    async for session in get_session():
        exercise = Exercise(
            name="Push-up",
            body_part="chest",
            primary_muscles="pectoralis major, triceps, anterior deltoid",
            secondary_muscles="core",
            equipment="bodyweight",
            instructions="Lower body until chest nearly touches floor, then push back up",
            category=ExerciseCategory.STRENGTH,
        )
        session.add(exercise)
        await session.commit()
        await session.refresh(exercise)
        return exercise


@pytest.mark.asyncio
async def test_create_routine(client: AsyncClient, sample_exercise):
    response = await client.post(
        "/api/routines",
        json={
            "name": "Push Day",
            "description": "Upper body push routine",
            "icon": "dumbbell",
            "phases": "warmup,work,cooldown",
            "exercises": [
                {
                    "exercise_id": sample_exercise.id,
                    "order": 0,
                    "phase": "work",
                    "sets": 3,
                    "target_reps": "8-12",
                    "target_rpe": 8,
                    "rest_seconds": 90,
                    "notes": "Focus on form"
                }
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Push Day"
    assert data["description"] == "Upper body push routine"
    assert data["icon"] == "dumbbell"
    assert data["phases"] == "warmup,work,cooldown"
    assert len(data["exercises"]) == 1
    assert data["exercises"][0]["exercise_id"] == sample_exercise.id
    assert data["exercises"][0]["sets"] == 3
    assert "id" in data
    assert "owner_id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_routine_without_exercises(client: AsyncClient):
    response = await client.post(
        "/api/routines",
        json={
            "name": "Empty Routine",
            "description": "No exercises yet",
            "exercises": [],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Empty Routine"
    assert data["exercises"] == []


@pytest.mark.asyncio
async def test_list_routines(client: AsyncClient, sample_exercise):
    # Create a few routines
    for i in range(5):
        await client.post(
            "/api/routines",
            json={"name": f"Routine {i}", "description": f"Description {i}", "exercises": []},
        )

    # List all
    response = await client.get("/api/routines")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    # Check all routines are returned (order not guaranteed with same timestamp)
    names = {r["name"] for r in data}
    assert names == {"Routine 0", "Routine 1", "Routine 2", "Routine 3", "Routine 4"}
    # Test limit
    response = await client.get("/api/routines?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    # Test skip
    response = await client.get("/api/routines?skip=3&limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_routine(client: AsyncClient, sample_exercise):
    # Create routine
    create_response = await client.post(
        "/api/routines",
        json={
            "name": "Test Routine",
            "exercises": [
                {
                    "exercise_id": sample_exercise.id,
                    "order": 0,
                    "phase": "work",
                    "sets": 3,
                }
            ],
        },
    )
    routine_id = create_response.json()["id"]

    # Get the routine
    response = await client.get(f"/api/routines/{routine_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == routine_id
    assert data["name"] == "Test Routine"
    assert len(data["exercises"]) == 1
    assert data["exercises"][0]["exercise"]["name"] == "Push-up"


@pytest.mark.asyncio
async def test_get_routine_not_found(client: AsyncClient):
    response = await client.get("/api/routines/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Routine not found"


@pytest.mark.asyncio
async def test_update_routine(client: AsyncClient, sample_exercise):
    # Create routine
    create_response = await client.post(
        "/api/routines",
        json={
            "name": "Original Name",
            "description": "Original description",
            "exercises": [
                {
                    "exercise_id": sample_exercise.id,
                    "order": 0,
                    "phase": "work",
                    "sets": 3,
                }
            ],
        },
    )
    routine_id = create_response.json()["id"]

    # Update routine
    response = await client.put(
        f"/api/routines/{routine_id}",
        json={
            "name": "Updated Name",
            "description": "Updated description",
            "exercises": [
                {
                    "exercise_id": sample_exercise.id,
                    "order": 0,
                    "phase": "work",
                    "sets": 4,
                    "target_reps": "10-15",
                }
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated description"
    assert data["exercises"][0]["sets"] == 4
    assert data["exercises"][0]["target_reps"] == "10-15"


@pytest.mark.asyncio
async def test_update_routine_partial(client: AsyncClient, sample_exercise):
    # Create routine
    create_response = await client.post(
        "/api/routines",
        json={
            "name": "Partial Update Test",
            "description": "Will update name only",
            "exercises": [
                {
                    "exercise_id": sample_exercise.id,
                    "order": 0,
                    "phase": "work",
                    "sets": 3,
                }
            ],
        },
    )
    routine_id = create_response.json()["id"]

    # Partial update - only name
    response = await client.put(
        f"/api/routines/{routine_id}",
        json={"name": "New Name Only"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name Only"
    assert data["description"] == "Will update name only"  # Unchanged
    assert len(data["exercises"]) == 1  # Unchanged


@pytest.mark.asyncio
async def test_update_routine_not_found(client: AsyncClient):
    response = await client.put(
        "/api/routines/999",
        json={"name": "Does not exist"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Routine not found"


@pytest.mark.asyncio
async def test_delete_routine(client: AsyncClient, sample_exercise):
    # Create routine
    create_response = await client.post(
        "/api/routines",
        json={
            "name": "To Delete",
            "exercises": [
                {
                    "exercise_id": sample_exercise.id,
                    "order": 0,
                    "phase": "work",
                    "sets": 3,
                }
            ],
        },
    )
    routine_id = create_response.json()["id"]

    # Delete the routine
    response = await client.delete(f"/api/routines/{routine_id}")
    assert response.status_code == 204

    # Verify it's gone
    response = await client.get(f"/api/routines/{routine_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_routine_not_found(client: AsyncClient):
    response = await client.delete("/api/routines/999")
    assert response.status_code == 404
