import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.database import init_db, reset_engine, get_session_maker
from app.models import Exercise, ExerciseCategory, Routine, RoutineExercise, RoutinePhase
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
async def sample_exercise():
    """Create a sample exercise for testing workouts."""
    from app.core.database import get_session_maker

    session_maker = get_session_maker()
    async with session_maker() as session:
        exercise = Exercise(
            name="Push-up",
            body_part="chest",
            primary_muscles="pectoralis major, triceps, anterior deltoid",
            secondary_muscles="core",
            equipment="bodyweight",
            instructions="Standard push-up",
            category=ExerciseCategory.STRENGTH,
        )
        session.add(exercise)
        await session.commit()
        await session.refresh(exercise)
        return exercise


@pytest.fixture
async def sample_routine(sample_exercise):
    """Create a sample routine for testing workouts."""
    from app.core.database import get_session

    session_maker = get_session_maker()
    async with session_maker() as session:
        routine = Routine(
            name="Push Day",
            description="Upper body push routine",
            owner_id=1,
        )
        session.add(routine)
        await session.flush()

        routine_exercise = RoutineExercise(
            routine_id=routine.id,
            exercise_id=sample_exercise.id,
            order=1,
            phase=RoutinePhase.WORK,
            sets=3,
            target_reps="8-12",
            target_rpe=8,
            rest_seconds=90,
        )
        session.add(routine_exercise)
        await session.commit()
        await session.refresh(routine)
        return routine


@pytest.mark.asyncio
async def test_create_workout(client: AsyncClient, sample_routine, sample_exercise):
    response = await client.post(
        "/api/workouts",
        json={
            "routine_id": sample_routine.id,
            "name": "Push Day Workout",
            "notes": "Feeling strong today",
            "entries": [
                {
                    "exercise_id": sample_exercise.id,
                    "order": 1,
                    "notes": "First set was easy",
                    "sets": [
                        {"set_phase": "warmup", "weight": 0, "reps": 10, "rpe": 5, "completed": True},
                        {"set_phase": "work", "weight": 0, "reps": 12, "rpe": 8, "completed": True},
                        {"set_phase": "work", "weight": 0, "reps": 10, "rpe": 9, "completed": True},
                    ],
                }
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Push Day Workout"
    assert data["routine_id"] == sample_routine.id
    assert data["notes"] == "Feeling strong today"
    assert len(data["entries"]) == 1
    assert data["entries"][0]["exercise_id"] == sample_exercise.id
    assert len(data["entries"][0]["sets"]) == 3
    assert data["entries"][0]["sets"][0]["set_phase"] == "warmup"
    assert data["entries"][0]["sets"][1]["set_phase"] == "work"
    assert "id" in data
    assert "started_at" in data
    assert "completed_at" not in data or data["completed_at"] is None
    assert "duration_seconds" not in data or data["duration_seconds"] is None


@pytest.mark.asyncio
async def test_create_workout_without_routine(client: AsyncClient, sample_exercise):
    response = await client.post(
        "/api/workouts",
        json={
            "name": "Custom Workout",
            "entries": [
                {
                    "exercise_id": sample_exercise.id,
                    "order": 1,
                    "sets": [{"set_phase": "work", "weight": 50, "reps": 5, "rpe": 8, "completed": True}],
                }
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Custom Workout"
    assert data["routine_id"] is None
    assert len(data["entries"]) == 1


@pytest.mark.asyncio
async def test_create_workout_without_entries(client: AsyncClient, sample_routine):
    response = await client.post(
        "/api/workouts",
        json={"routine_id": sample_routine.id, "name": "Empty Workout"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Empty Workout"
    assert data["entries"] == []


@pytest.mark.asyncio
async def test_list_workouts(client: AsyncClient, sample_routine, sample_exercise):
    # Create a few workouts
    for i in range(3):
        await client.post(
            "/api/workouts",
            json={
                "routine_id": sample_routine.id,
                "name": f"Workout {i}",
                "entries": [
                    {
                        "exercise_id": sample_exercise.id,
                        "order": 1,
                        "sets": [{"set_phase": "work", "reps": 10, "completed": True}],
                    }
                ],
            },
        )

    response = await client.get("/api/workouts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # Should be ordered by started_at desc (newest first)
    assert data[0]["name"] == "Workout 2"
    assert data[2]["name"] == "Workout 0"


@pytest.mark.asyncio
async def test_list_workouts_with_routine_filter(client: AsyncClient, sample_routine, sample_exercise):
    # Create another routine
    from app.core.database import get_session

    async for session in get_session():
        routine2 = Routine(name="Pull Day", owner_id=1)
        session.add(routine2)
        await session.commit()
        await session.refresh(routine2)
        routine2_id = routine2.id

    # Create workouts for both routines
    await client.post("/api/workouts", json={"routine_id": sample_routine.id, "name": "Push 1"})
    await client.post("/api/workouts", json={"routine_id": routine2_id, "name": "Pull 1"})

    response = await client.get(f"/api/workouts?routine_id={sample_routine.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Push 1"
    assert data[0]["routine_id"] == sample_routine.id


@pytest.mark.asyncio
async def test_get_workout(client: AsyncClient, sample_routine, sample_exercise):
    create_response = await client.post(
        "/api/workouts",
        json={
            "routine_id": sample_routine.id,
            "name": "Test Workout",
            "entries": [
                {
                    "exercise_id": sample_exercise.id,
                    "order": 1,
                    "sets": [{"set_phase": "work", "weight": 60, "reps": 8, "rpe": 8, "completed": True}],
                }
            ],
        },
    )
    workout_id = create_response.json()["id"]

    response = await client.get(f"/api/workouts/{workout_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workout_id
    assert data["name"] == "Test Workout"
    assert data["routine"]["id"] == sample_routine.id
    assert len(data["entries"]) == 1
    assert data["entries"][0]["exercise"]["name"] == "Push-up"
    assert data["entries"][0]["sets"][0]["weight"] == 60
    assert data["entries"][0]["sets"][0]["reps"] == 8


@pytest.mark.asyncio
async def test_get_workout_not_found(client: AsyncClient):
    response = await client.get("/api/workouts/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Workout not found"


@pytest.mark.asyncio
async def test_update_workout(client: AsyncClient, sample_routine, sample_exercise):
    create_response = await client.post(
        "/api/workouts", json={"routine_id": sample_routine.id, "name": "Original Name", "notes": "Original notes"}
    )
    workout_id = create_response.json()["id"]

    response = await client.put(
        f"/api/workouts/{workout_id}", json={"name": "Updated Name", "notes": "Updated notes"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["notes"] == "Updated notes"


@pytest.mark.asyncio
async def test_update_workout_routine(client: AsyncClient, sample_routine, sample_exercise):
    # Create second routine
    from app.core.database import get_session

    async for session in get_session():
        routine2 = Routine(name="Routine 2", owner_id=1)
        session.add(routine2)
        await session.commit()
        await session.refresh(routine2)
        routine2_id = routine2.id

    create_response = await client.post("/api/workouts", json={"routine_id": sample_routine.id, "name": "Workout"})
    workout_id = create_response.json()["id"]

    # Update to different routine
    response = await client.put(f"/api/workouts/{workout_id}", json={"routine_id": routine2_id})
    assert response.status_code == 200
    assert response.json()["routine_id"] == routine2_id

    # Remove routine (set to null/0)
    response = await client.put(f"/api/workouts/{workout_id}", json={"routine_id": 0})
    assert response.status_code == 200
    assert response.json()["routine_id"] is None


@pytest.mark.asyncio
async def test_update_workout_not_found(client: AsyncClient):
    response = await client.put("/api/workouts/999", json={"name": "Updated"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Workout not found"


@pytest.mark.asyncio
async def test_delete_workout(client: AsyncClient, sample_routine, sample_exercise):
    create_response = await client.post("/api/workouts", json={"routine_id": sample_routine.id, "name": "To Delete"})
    workout_id = create_response.json()["id"]

    response = await client.delete(f"/api/workouts/{workout_id}")
    assert response.status_code == 204

    # Verify deleted
    get_response = await client.get(f"/api/workouts/{workout_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_workout_not_found(client: AsyncClient):
    response = await client.delete("/api/workouts/999")
    assert response.status_code == 404


# Entry tests
@pytest.mark.asyncio
async def test_add_entry_to_workout(client: AsyncClient, sample_routine, sample_exercise):
    workout_response = await client.post("/api/workouts", json={"routine_id": sample_routine.id, "name": "Workout"})
    workout_id = workout_response.json()["id"]

    response = await client.post(
        f"/api/workouts/{workout_id}/entries",
        json={
            "exercise_id": sample_exercise.id,
            "order": 1,
            "notes": "Added entry",
            "sets": [{"set_phase": "work", "weight": 70, "reps": 6, "rpe": 9, "completed": True}],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["entries"]) == 1
    assert data["entries"][0]["exercise_id"] == sample_exercise.id
    assert data["entries"][0]["notes"] == "Added entry"
    assert len(data["entries"][0]["sets"]) == 1
    assert data["entries"][0]["sets"][0]["weight"] == 70


@pytest.mark.asyncio
async def test_add_entry_auto_order(client: AsyncClient, sample_routine, sample_exercise):
    workout_response = await client.post("/api/workouts", json={"routine_id": sample_routine.id, "name": "Workout"})
    workout_id = workout_response.json()["id"]

    # Add first entry without order
    await client.post(
        f"/api/workouts/{workout_id}/entries",
        json={"exercise_id": sample_exercise.id, "sets": [{"set_phase": "work", "reps": 10, "completed": True}]},
    )

    # Add second entry without order - should get order 2
    response = await client.post(
        f"/api/workouts/{workout_id}/entries",
        json={"exercise_id": sample_exercise.id, "sets": [{"set_phase": "work", "reps": 10, "completed": True}]},
    )
    assert response.status_code == 201
    data = response.json()
    # Entries should be ordered 1, 2
    assert len(data["entries"]) == 2
    assert data["entries"][0]["order"] == 1
    assert data["entries"][1]["order"] == 2


@pytest.mark.asyncio
async def test_update_entry(client: AsyncClient, sample_routine, sample_exercise):
    workout_response = await client.post(
        "/api/workouts",
        json={
            "routine_id": sample_routine.id,
            "name": "Workout",
            "entries": [
                {
                    "exercise_id": sample_exercise.id,
                    "order": 1,
                    "sets": [{"set_phase": "work", "reps": 10, "completed": True}],
                }
            ],
        },
    )
    workout_id = workout_response.json()["id"]
    entry_id = workout_response.json()["entries"][0]["id"]

    response = await client.put(
        f"/api/workouts/entries/{entry_id}",
        json={"notes": "Updated notes", "sets": [{"set_phase": "work", "weight": 80, "reps": 5, "completed": True}]},
    )
    assert response.status_code == 200
    data = response.json()
    entry = data["entries"][0]
    assert entry["notes"] == "Updated notes"
    assert entry["sets"][0]["weight"] == 80
    assert entry["sets"][0]["reps"] == 5


@pytest.mark.asyncio
async def test_delete_entry(client: AsyncClient, sample_routine, sample_exercise):
    workout_response = await client.post(
        "/api/workouts",
        json={
            "routine_id": sample_routine.id,
            "name": "Workout",
            "entries": [
                {"exercise_id": sample_exercise.id, "order": 1, "sets": [{"set_phase": "work", "reps": 10}]},
                {"exercise_id": sample_exercise.id, "order": 2, "sets": [{"set_phase": "work", "reps": 10}]},
            ],
        },
    )
    workout_id = workout_response.json()["id"]
    entry_id = workout_response.json()["entries"][0]["id"]

    response = await client.delete(f"/api/workouts/entries/{entry_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 1
    assert data["entries"][0]["order"] == 2


# Set tests
@pytest.mark.asyncio
async def test_add_set_to_entry(client: AsyncClient, sample_routine, sample_exercise):
    workout_response = await client.post(
        "/api/workouts",
        json={
            "routine_id": sample_routine.id,
            "name": "Workout",
            "entries": [
                {"exercise_id": sample_exercise.id, "order": 1, "sets": [{"set_phase": "work", "reps": 10}]},
            ],
        },
    )
    workout_id = workout_response.json()["id"]
    entry_id = workout_response.json()["entries"][0]["id"]

    response = await client.post(
        f"/api/workouts/entries/{entry_id}/sets",
        json={"set_phase": "work", "weight": 100, "reps": 3, "rpe": 10, "completed": True},
    )
    assert response.status_code == 201
    data = response.json()
    entry = data["entries"][0]
    assert len(entry["sets"]) == 2
    assert entry["sets"][1]["weight"] == 100
    assert entry["sets"][1]["reps"] == 3


@pytest.mark.asyncio
async def test_update_set(client: AsyncClient, sample_routine, sample_exercise):
    workout_response = await client.post(
        "/api/workouts",
        json={
            "routine_id": sample_routine.id,
            "name": "Workout",
            "entries": [
                {"exercise_id": sample_exercise.id, "order": 1, "sets": [{"set_phase": "work", "reps": 10}]},
            ],
        },
    )
    workout_id = workout_response.json()["id"]
    entry_id = workout_response.json()["entries"][0]["id"]
    set_id = workout_response.json()["entries"][0]["sets"][0]["id"]

    response = await client.put(
        f"/api/workouts/sets/{set_id}",
        json={"weight": 120, "reps": 2, "completed": True},
    )
    assert response.status_code == 200
    data = response.json()
    set_data = data["entries"][0]["sets"][0]
    assert set_data["weight"] == 120
    assert set_data["reps"] == 2
    assert set_data["completed"] is True


@pytest.mark.asyncio
async def test_delete_set(client: AsyncClient, sample_routine, sample_exercise):
    workout_response = await client.post(
        "/api/workouts",
        json={
            "routine_id": sample_routine.id,
            "name": "Workout",
            "entries": [
                {
                    "exercise_id": sample_exercise.id,
                    "order": 1,
                    "sets": [
                        {"set_phase": "work", "reps": 10},
                        {"set_phase": "work", "reps": 8},
                    ],
                },
            ],
        },
    )
    workout_id = workout_response.json()["id"]
    entry_id = workout_response.json()["entries"][0]["id"]
    set_id = workout_response.json()["entries"][0]["sets"][0]["id"]

    response = await client.delete(f"/api/workouts/sets/{set_id}")
    assert response.status_code == 200
    data = response.json()
    entry = data["entries"][0]
    assert len(entry["sets"]) == 1
    assert entry["sets"][0]["reps"] == 8


# Complete workout test
@pytest.mark.asyncio
async def test_complete_workout(client: AsyncClient, sample_routine, sample_exercise):
    workout_response = await client.post(
        "/api/workouts", json={"routine_id": sample_routine.id, "name": "Workout to Complete"}
    )
    workout_id = workout_response.json()["id"]

    response = await client.post(f"/api/workouts/{workout_id}/complete")
    assert response.status_code == 200
    data = response.json()
    assert data["completed_at"] is not None
    assert data["duration_seconds"] is not None
    assert data["duration_seconds"] >= 0


@pytest.mark.asyncio
async def test_complete_workout_already_completed(client: AsyncClient, sample_routine, sample_exercise):
    workout_response = await client.post("/api/workouts", json={"routine_id": sample_routine.id, "name": "Workout"})
    workout_id = workout_response.json()["id"]

    # Complete once
    await client.post(f"/api/workouts/{workout_id}/complete")

    # Try to complete again
    response = await client.post(f"/api/workouts/{workout_id}/complete")
    assert response.status_code == 400
    assert response.json()["detail"] == "Workout already completed"

