from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_session
from app.models import (
    User,
    Exercise,
    Routine,
    WorkoutSession,
    WorkoutEntry,
    WorkoutSet,
    SetPhase,
)
from app.schemas import (
    WorkoutSessionCreate,
    WorkoutSessionUpdate,
    WorkoutSessionResponse,
    WorkoutEntryCreate,
    WorkoutEntryUpdate,
    WorkoutSetCreate,
    WorkoutSetUpdate,
)

router = APIRouter(prefix="/workouts", tags=["workouts"])


def get_current_user_id() -> int:
    """Placeholder for auth - returns a default user ID for now."""
    return 1


async def ensure_user(session: AsyncSession, user_id: int) -> User:
    """Ensure user exists, create if not (for development)."""
    from app.models import WeightUnit

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(id=user_id, email="test@example.com", weight_unit=WeightUnit.KG)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


def _load_workout_session_query(session: AsyncSession, workout_id: int, user_id: int):
    """Build query to load workout session with all relationships."""
    return (
        select(WorkoutSession)
        .where(WorkoutSession.id == workout_id, WorkoutSession.user_id == user_id)
        .options(
            selectinload(WorkoutSession.entries).selectinload(WorkoutEntry.exercise),
            selectinload(WorkoutSession.entries).selectinload(WorkoutEntry.sets),
            selectinload(WorkoutSession.routine),
        )
    )


@router.post("", response_model=WorkoutSessionResponse, status_code=201)
async def create_workout(
    workout_in: WorkoutSessionCreate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Create a new workout session with optional entries and sets."""
    user = await ensure_user(session, user_id)

    # Verify routine exists if provided
    if workout_in.routine_id:
        routine_result = await session.execute(
            select(Routine).where(Routine.id == workout_in.routine_id, Routine.owner_id == user_id)
        )
        routine = routine_result.scalar_one_or_none()
        if not routine:
            raise HTTPException(status_code=404, detail="Routine not found")

    workout = WorkoutSession(
        user_id=user_id,
        routine_id=workout_in.routine_id,
        name=workout_in.name,
        notes=workout_in.notes,
    )
    session.add(workout)
    await session.flush()

    # Create entries and sets
    for entry_data in workout_in.entries:
        exercise_result = await session.execute(
            select(Exercise).where(Exercise.id == entry_data.exercise_id)
        )
        exercise = exercise_result.scalar_one_or_none()
        if not exercise:
            raise HTTPException(status_code=404, detail=f"Exercise {entry_data.exercise_id} not found")

        entry = WorkoutEntry(
            workout_session_id=workout.id,
            exercise_id=entry_data.exercise_id,
            order=entry_data.order,
            phase=entry_data.phase,
            weight_unit=entry_data.weight_unit or user.weight_unit,
            notes=entry_data.notes,
        )
        session.add(entry)
        await session.flush()

        for set_data in entry_data.sets:
            set_obj = WorkoutSet(
                workout_entry_id=entry.id,
                set_phase=set_data.set_phase,
                weight=set_data.weight,
                reps=set_data.reps,
                rpe=set_data.rpe,
                completed=set_data.completed,
            )
            session.add(set_obj)

    await session.commit()
    await session.refresh(workout)

    # Reload with relationships
    result = await session.execute(_load_workout_session_query(session, workout.id, user_id))
    return result.unique().scalar_one()


@router.get("", response_model=List[WorkoutSessionResponse])
async def list_workouts(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    routine_id: Optional[int] = Query(None),
):
    """List workout sessions for the current user."""
    await ensure_user(session, user_id)

    query = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == user_id)
        .options(
            selectinload(WorkoutSession.entries).selectinload(WorkoutEntry.exercise),
            selectinload(WorkoutSession.entries).selectinload(WorkoutEntry.sets),
            selectinload(WorkoutSession.routine),
        )
        .order_by(WorkoutSession.started_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if routine_id:
        query = query.where(WorkoutSession.routine_id == routine_id)

    result = await session.execute(query)
    workouts = result.unique().scalars().all()
    return workouts


@router.get("/{workout_id}", response_model=WorkoutSessionResponse)
async def get_workout(
    workout_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Get a specific workout session by ID."""
    await ensure_user(session, user_id)

    result = await session.execute(_load_workout_session_query(session, workout_id, user_id))
    workout = result.unique().scalar_one_or_none()

    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    return workout


@router.put("/{workout_id}", response_model=WorkoutSessionResponse)
async def update_workout(
    workout_id: int,
    workout_in: WorkoutSessionUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Update a workout session (metadata only - use entry/set endpoints for details)."""
    await ensure_user(session, user_id)

    result = await session.execute(
        select(WorkoutSession).where(WorkoutSession.id == workout_id, WorkoutSession.user_id == user_id)
    )
    workout = result.scalar_one_or_none()

    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    # Verify routine exists if provided
    if workout_in.routine_id is not None:
        if workout_in.routine_id > 0:
            routine_result = await session.execute(
                select(Routine).where(Routine.id == workout_in.routine_id, Routine.user_id == user_id)
            )
            routine = routine_result.scalar_one_or_none()
            if not routine:
                raise HTTPException(status_code=404, detail="Routine not found")
        workout.routine_id = workout_in.routine_id if workout_in.routine_id > 0 else None

    update_data = workout_in.model_dump(exclude_unset=True, exclude={"routine_id"})
    for field, value in update_data.items():
        setattr(workout, field, value)

    await session.commit()
    await session.refresh(workout)

    # Reload with relationships
    result = await session.execute(_load_workout_session_query(session, workout_id, user_id))
    return result.unique().scalar_one()


@router.delete("/{workout_id}", status_code=204)
async def delete_workout(
    workout_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Delete a workout session."""
    await ensure_user(session, user_id)

    result = await session.execute(
        select(WorkoutSession).where(WorkoutSession.id == workout_id, WorkoutSession.user_id == user_id)
    )
    workout = result.scalar_one_or_none()

    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    await session.delete(workout)
    await session.commit()
    return None


# Entry endpoints
@router.post("/{workout_id}/entries", response_model=WorkoutSessionResponse, status_code=201)
async def add_entry_to_workout(
    workout_id: int,
    entry_in: WorkoutEntryCreate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Add an exercise entry to a workout session."""
    await ensure_user(session, user_id)

    # Verify workout exists and belongs to user
    workout_result = await session.execute(
        select(WorkoutSession).where(WorkoutSession.id == workout_id, WorkoutSession.user_id == user_id)
    )
    workout = workout_result.scalar_one_or_none()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    # Verify exercise exists
    exercise_result = await session.execute(select(Exercise).where(Exercise.id == entry_in.exercise_id))
    exercise = exercise_result.scalar_one_or_none()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    # Determine order if not provided
    if entry_in.order is None:
        max_order_result = await session.execute(
            select(func.max(WorkoutEntry.order)).where(WorkoutEntry.workout_session_id == workout_id)
        )
        max_order = max_order_result.scalar() or 0
        entry_in.order = max_order + 1

    entry = WorkoutEntry(
        workout_session_id=workout_id,
        exercise_id=entry_in.exercise_id,
        order=entry_in.order,
        notes=entry_in.notes,
    )
    session.add(entry)
    await session.flush()

    for set_data in entry_in.sets:
        set_obj = WorkoutSet(
            workout_entry_id=entry.id,
            set_phase=set_data.set_phase,
            weight=set_data.weight,
            reps=set_data.reps,
            rpe=set_data.rpe,
            completed=set_data.completed,
        )
        session.add(set_obj)

    await session.commit()

    # Reload workout with relationships
    result = await session.execute(_load_workout_session_query(session, workout_id, user_id))
    return result.unique().scalar_one()


@router.put("/entries/{entry_id}", response_model=WorkoutSessionResponse)
async def update_entry(
    entry_id: int,
    entry_in: WorkoutEntryUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Update a workout entry."""
    await ensure_user(session, user_id)

    # Verify entry exists and belongs to user's workout
    entry_result = await session.execute(
        select(WorkoutEntry)
        .join(WorkoutSession)
        .where(WorkoutEntry.id == entry_id, WorkoutSession.user_id == user_id)
        .options(selectinload(WorkoutEntry.sets))
    )
    entry = entry_result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Verify exercise if provided
    if entry_in.exercise_id is not None:
        exercise_result = await session.execute(select(Exercise).where(Exercise.id == entry_in.exercise_id))
        exercise = exercise_result.scalar_one_or_none()
        if not exercise:
            raise HTTPException(status_code=404, detail="Exercise not found")

    update_data = entry_in.model_dump(exclude_unset=True, exclude={"sets"})
    for field, value in update_data.items():
        setattr(entry, field, value)

    # Update sets if provided
    if entry_in.sets is not None:
        # Delete existing sets
        for existing_set in entry.sets:
            await session.delete(existing_set)
        await session.flush()

        # Create new sets
        for set_data in entry_in.sets:
            set_obj = WorkoutSet(
                workout_entry_id=entry.id,
                set_phase=set_data.set_phase,
                weight=set_data.weight,
                reps=set_data.reps,
                rpe=set_data.rpe,
                completed=set_data.completed,
            )
            session.add(set_obj)

    await session.commit()

    # Reload workout with relationships
    result = await session.execute(_load_workout_session_query(session, entry.workout_session_id, user_id))
    return result.unique().scalar_one()


@router.delete("/entries/{entry_id}", response_model=WorkoutSessionResponse)
async def delete_entry(
    entry_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Delete a workout entry."""
    await ensure_user(session, user_id)

    entry_result = await session.execute(
        select(WorkoutEntry)
        .join(WorkoutSession)
        .where(WorkoutEntry.id == entry_id, WorkoutSession.user_id == user_id)
    )
    entry = entry_result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    workout_id = entry.workout_session_id
    await session.delete(entry)
    await session.commit()

    # Reload workout with relationships
    result = await session.execute(_load_workout_session_query(session, workout_id, user_id))
    return result.unique().scalar_one()


# Set endpoints
@router.post("/entries/{entry_id}/sets", response_model=WorkoutSessionResponse, status_code=201)
async def add_set_to_entry(
    entry_id: int,
    set_in: WorkoutSetCreate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Add a set to a workout entry."""
    await ensure_user(session, user_id)

    entry_result = await session.execute(
        select(WorkoutEntry)
        .join(WorkoutSession)
        .where(WorkoutEntry.id == entry_id, WorkoutSession.user_id == user_id)
    )
    entry = entry_result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    set_obj = WorkoutSet(
        workout_entry_id=entry_id,
        set_phase=set_in.set_phase,
        weight=set_in.weight,
        reps=set_in.reps,
        rpe=set_in.rpe,
        completed=set_in.completed,
    )
    session.add(set_obj)
    await session.commit()

    # Reload workout with relationships
    result = await session.execute(_load_workout_session_query(session, entry.workout_session_id, user_id))
    return result.unique().scalar_one()


@router.put("/sets/{set_id}", response_model=WorkoutSessionResponse)
async def update_set(
    set_id: int,
    set_in: WorkoutSetUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Update a workout set."""
    await ensure_user(session, user_id)

    set_result = await session.execute(
        select(WorkoutSet)
        .join(WorkoutEntry)
        .join(WorkoutSession)
        .where(WorkoutSet.id == set_id, WorkoutSession.user_id == user_id)
    )
    set_obj = set_result.scalar_one_or_none()
    if not set_obj:
        raise HTTPException(status_code=404, detail="Set not found")

    update_data = set_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(set_obj, field, value)

    await session.commit()

    # Reload workout with relationships
    entry_result = await session.execute(
        select(WorkoutEntry).where(WorkoutEntry.id == set_obj.workout_entry_id)
    )
    entry = entry_result.scalar_one()
    result = await session.execute(_load_workout_session_query(session, entry.workout_session_id, user_id))
    return result.unique().scalar_one()


@router.delete("/sets/{set_id}", response_model=WorkoutSessionResponse)
async def delete_set(
    set_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Delete a workout set."""
    await ensure_user(session, user_id)

    set_result = await session.execute(
        select(WorkoutSet)
        .join(WorkoutEntry)
        .join(WorkoutSession)
        .where(WorkoutSet.id == set_id, WorkoutSession.user_id == user_id)
    )
    set_obj = set_result.scalar_one_or_none()
    if not set_obj:
        raise HTTPException(status_code=404, detail="Set not found")

    entry_id = set_obj.workout_entry_id
    await session.delete(set_obj)
    await session.commit()

    # Reload workout with relationships
    entry_result = await session.execute(select(WorkoutEntry).where(WorkoutEntry.id == entry_id))
    entry = entry_result.scalar_one()
    result = await session.execute(_load_workout_session_query(session, entry.workout_session_id, user_id))
    return result.unique().scalar_one()


# Complete workout endpoint
@router.post("/{workout_id}/complete", response_model=WorkoutSessionResponse)
async def complete_workout(
    workout_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Mark a workout as completed with duration."""
    await ensure_user(session, user_id)

    result = await session.execute(
        select(WorkoutSession).where(WorkoutSession.id == workout_id, WorkoutSession.user_id == user_id)
    )
    workout = result.scalar_one_or_none()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    if workout.completed_at:
        raise HTTPException(status_code=400, detail="Workout already completed")

    from datetime import datetime, timezone

    workout.completed_at = datetime.now(timezone.utc)
    if workout.started_at:
        duration = int((workout.completed_at - workout.started_at).total_seconds())
        workout.duration_seconds = duration

    await session.commit()
    await session.refresh(workout)

    # Reload with relationships
    result = await session.execute(_load_workout_session_query(session, workout_id, user_id))
    return result.unique().scalar_one()

