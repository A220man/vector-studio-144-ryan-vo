from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_session
from app.models import Exercise, User, ExerciseCategory
from app.schemas import ExerciseCreate, ExerciseUpdate, ExerciseResponse

router = APIRouter(prefix="/exercises", tags=["exercises"])


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


@router.post("", response_model=ExerciseResponse, status_code=201)
async def create_exercise(
    exercise_in: ExerciseCreate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Create a new exercise."""
    await ensure_user(session, user_id)

    exercise = Exercise(
        name=exercise_in.name,
        category=exercise_in.category,
        primary_muscles=exercise_in.primary_muscles,
        secondary_muscles=exercise_in.secondary_muscles,
        equipment=exercise_in.equipment,
        instructions=exercise_in.instructions,
        weight_unit=exercise_in.weight_unit,
    )
    session.add(exercise)
    await session.commit()
    await session.refresh(exercise)
    return exercise


@router.get("", response_model=List[ExerciseResponse])
async def list_exercises(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[ExerciseCategory] = Query(None),
    muscle: Optional[str] = Query(None),
    equipment: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """List exercises with optional filters."""
    await ensure_user(session, user_id)

    query = select(Exercise)

    if category:
        query = query.where(Exercise.category == category)

    if muscle:
        query = query.where(
            or_(
                Exercise.primary_muscles.contains([muscle]),
                Exercise.secondary_muscles.contains([muscle]),
            )
        )

    if equipment:
        query = query.where(Exercise.equipment.contains([equipment]))

    if search:
        query = query.where(Exercise.name.ilike(f"%{search}%"))

    query = query.order_by(Exercise.name).offset(skip).limit(limit)

    result = await session.execute(query)
    exercises = result.scalars().all()
    return exercises


@router.get("/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise(
    exercise_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Get a specific exercise by ID."""
    await ensure_user(session, user_id)

    result = await session.execute(select(Exercise).where(Exercise.id == exercise_id))
    exercise = result.scalar_one_or_none()

    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    return exercise


@router.put("/{exercise_id}", response_model=ExerciseResponse)
async def update_exercise(
    exercise_id: int,
    exercise_in: ExerciseUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Update an exercise."""
    await ensure_user(session, user_id)

    result = await session.execute(select(Exercise).where(Exercise.id == exercise_id))
    exercise = result.scalar_one_or_none()

    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    update_data = exercise_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(exercise, field, value)

    await session.commit()
    await session.refresh(exercise)
    return exercise


@router.delete("/{exercise_id}", status_code=204)
async def delete_exercise(
    exercise_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """Delete an exercise."""
    await ensure_user(session, user_id)

    result = await session.execute(select(Exercise).where(Exercise.id == exercise_id))
    exercise = result.scalar_one_or_none()

    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    await session.delete(exercise)
    await session.commit()
    return None

