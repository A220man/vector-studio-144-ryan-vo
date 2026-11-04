from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.database import get_session
from app.core.config import settings
from app.models import Routine, RoutineExercise, Exercise, RoutinePhase, User
from app.schemas import (
    RoutineCreate,
    RoutineUpdate,
    RoutineResponse,
    RoutineExerciseCreate,
)

router = APIRouter(prefix="/routines", tags=["routines"])


def get_current_user_id() -> int:
    """Placeholder for auth - returns a default user ID for now."""
    return 1


async def ensure_user(session: AsyncSession, user_id: int) -> User:
    """Ensure user exists, create if not (for development)."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(id=user_id, email=f"user{user_id}@example.com")
        session.add(user)
        await session.flush()
    return user


@router.post("", response_model=RoutineResponse, status_code=201)
async def create_routine(
    routine_in: RoutineCreate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Create a new routine with optional exercises."""
    await ensure_user(session, user_id)

    routine = Routine(
        name=routine_in.name,
        description=routine_in.description,
        icon=routine_in.icon,
        phases=routine_in.phases,
        owner_id=user_id,
    )
    session.add(routine)
    await session.flush()

    # Add exercises if provided
    for i, ex_in in enumerate(routine_in.exercises):
        routine_exercise = RoutineExercise(
            routine_id=routine.id,
            exercise_id=ex_in.exercise_id,
            order=ex_in.order or i,
            phase=ex_in.phase,
            sets=ex_in.sets,
            target_reps=ex_in.target_reps,
            target_rpe=ex_in.target_rpe,
            rest_seconds=ex_in.rest_seconds,
            notes=ex_in.notes,
        )
        session.add(routine_exercise)

    await session.commit()
    # Reload with relationships
    result = await session.execute(
        select(Routine)
        .where(Routine.id == routine.id)
        .options(selectinload(Routine.exercises).selectinload(RoutineExercise.exercise))
    )
    routine = result.scalar_one()
    return routine


@router.get("", response_model=List[RoutineResponse])
async def list_routines(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """List routines for the current user."""
    result = await session.execute(
        select(Routine)
        .where(Routine.owner_id == user_id)
        .options(selectinload(Routine.exercises).selectinload(RoutineExercise.exercise))
        .order_by(Routine.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    routines = result.scalars().all()
    return routines


@router.get("/{routine_id}", response_model=RoutineResponse)
async def get_routine(
    routine_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Get a specific routine by ID."""
    result = await session.execute(
        select(Routine)
        .where(Routine.id == routine_id, Routine.owner_id == user_id)
        .options(selectinload(Routine.exercises).selectinload(RoutineExercise.exercise))
    )
    routine = result.scalar_one_or_none()
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")
    return routine


@router.put("/{routine_id}", response_model=RoutineResponse)
async def update_routine(
    routine_id: int,
    routine_in: RoutineUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Update a routine."""
    result = await session.execute(
        select(Routine)
        .where(Routine.id == routine_id, Routine.owner_id == user_id)
        .options(selectinload(Routine.exercises).selectinload(RoutineExercise.exercise))
    )
    routine = result.scalar_one_or_none()
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")

    # Update routine fields
    update_data = routine_in.model_dump(exclude_unset=True, exclude={"exercises"})
    for field, value in update_data.items():
        setattr(routine, field, value)

    # Update exercises if provided
    if routine_in.exercises is not None:
        # Delete existing exercises
        for ex in routine.exercises:
            await session.delete(ex)
        await session.flush()

        # Add new exercises
        for i, ex_in in enumerate(routine_in.exercises):
            routine_exercise = RoutineExercise(
                routine_id=routine.id,
                exercise_id=ex_in.exercise_id,
                order=ex_in.order or i,
                phase=ex_in.phase,
                sets=ex_in.sets,
                target_reps=ex_in.target_reps,
                target_rpe=ex_in.target_rpe,
                rest_seconds=ex_in.rest_seconds,
                notes=ex_in.notes,
            )
            session.add(routine_exercise)

    await session.commit()
    # Expire to clear cached relationships
    await session.refresh(routine)
    # Reload with relationships
    result = await session.execute(
        select(Routine)
        .where(Routine.id == routine.id)
        .options(selectinload(Routine.exercises).selectinload(RoutineExercise.exercise))
    )
    routine = result.scalar_one()
    return routine


@router.delete("/{routine_id}", status_code=204)
async def delete_routine(
    routine_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Delete a routine."""
    result = await session.execute(
        select(Routine).where(Routine.id == routine_id, Routine.owner_id == user_id)
    )
    routine = result.scalar_one_or_none()
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")

    await session.delete(routine)
    await session.commit()
    return None
