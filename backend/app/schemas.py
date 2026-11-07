from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models import RoutinePhase, ExerciseCategory, WeightUnit, SetPhase


class ExerciseBase(BaseModel):
    name: str = Field(..., max_length=255)
    body_part: str = Field(..., max_length=100)
    primary_muscles: str
    secondary_muscles: Optional[str] = None
    equipment: Optional[str] = Field(None, max_length=100)
    instructions: Optional[str] = None
    category: ExerciseCategory = ExerciseCategory.STRENGTH
    weight_unit: Optional[WeightUnit] = None


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    body_part: Optional[str] = Field(None, max_length=100)
    primary_muscles: Optional[str] = None
    secondary_muscles: Optional[str] = None
    equipment: Optional[str] = Field(None, max_length=100)
    instructions: Optional[str] = None
    category: Optional[ExerciseCategory] = None
    weight_unit: Optional[WeightUnit] = None


class ExerciseResponse(ExerciseBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoutineExerciseBase(BaseModel):
    exercise_id: int
    order: int = 0
    phase: RoutinePhase = RoutinePhase.WORK
    sets: int = Field(..., ge=1)
    target_reps: Optional[str] = Field(None, max_length=50)
    target_rpe: Optional[int] = Field(None, ge=1, le=10)
    rest_seconds: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class RoutineExerciseCreate(RoutineExerciseBase):
    pass


class RoutineExerciseUpdate(BaseModel):
    exercise_id: Optional[int] = None
    order: Optional[int] = None
    phase: Optional[RoutinePhase] = None
    sets: Optional[int] = Field(None, ge=1)
    target_reps: Optional[str] = Field(None, max_length=50)
    target_rpe: Optional[int] = Field(None, ge=1, le=10)
    rest_seconds: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class RoutineExerciseResponse(RoutineExerciseBase):
    id: int
    routine_id: int
    created_at: datetime
    updated_at: datetime
    exercise: ExerciseResponse

    class Config:
        from_attributes = True


class RoutineBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    phases: Optional[str] = None


class RoutineCreate(RoutineBase):
    exercises: List[RoutineExerciseCreate] = []


class RoutineUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    phases: Optional[str] = None
    exercises: Optional[List[RoutineExerciseCreate]] = None


class RoutineResponse(RoutineBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    exercises: List[RoutineExerciseResponse] = []

    class Config:
        from_attributes = True


class WorkoutSetBase(BaseModel):
    set_phase: SetPhase = SetPhase.WORK
    weight: int = Field(..., ge=0)
    reps: int = Field(..., ge=0)
    rpe: Optional[int] = Field(None, ge=1, le=10)
    completed: bool = False


class WorkoutSetCreate(WorkoutSetBase):
    pass


class WorkoutSetUpdate(BaseModel):
    set_phase: Optional[SetPhase] = None
    weight: Optional[int] = Field(None, ge=0)
    reps: Optional[int] = Field(None, ge=0)
    rpe: Optional[int] = Field(None, ge=1, le=10)
    completed: Optional[bool] = None


class WorkoutSetResponse(WorkoutSetBase):
    id: int
    entry_id: int
    order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkoutEntryBase(BaseModel):
    exercise_id: int
    order: int = 0
    phase: RoutinePhase = RoutinePhase.WORK
    weight_unit: WeightUnit = WeightUnit.KG
    notes: Optional[str] = None


class WorkoutEntryCreate(WorkoutEntryBase):
    sets: List[WorkoutSetCreate] = []


class WorkoutEntryUpdate(BaseModel):
    exercise_id: Optional[int] = None
    order: Optional[int] = None
    phase: Optional[RoutinePhase] = None
    weight_unit: Optional[WeightUnit] = None
    notes: Optional[str] = None
    sets: Optional[List[WorkoutSetCreate]] = None


class WorkoutEntryResponse(WorkoutEntryBase):
    id: int
    session_id: int
    created_at: datetime
    updated_at: datetime
    sets: List[WorkoutSetResponse] = []
    exercise: ExerciseResponse

    class Config:
        from_attributes = True


class WorkoutSessionBase(BaseModel):
    routine_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None


class WorkoutSessionCreate(WorkoutSessionBase):
    entries: List[WorkoutEntryCreate] = []


class WorkoutSessionUpdate(BaseModel):
    routine_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    entries: Optional[List[WorkoutEntryCreate]] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = Field(None, ge=0)


class WorkoutSessionResponse(WorkoutSessionBase):
    id: int
    user_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    entries: List[WorkoutEntryResponse] = []

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None
    weight_unit: WeightUnit = WeightUnit.KG


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    weight_unit: Optional[WeightUnit] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
