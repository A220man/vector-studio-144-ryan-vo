from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class RoutinePhase(str, enum.Enum):
    MOBILITY = "mobility"
    WORK = "work"
    ACCESSORY = "accessory"
    COOLDOWN = "cooldown"


class ExerciseCategory(str, enum.Enum):
    STRENGTH = "strength"
    MOBILITY = "mobility"
    CARDIO = "cardio"
    STRETCHING = "stretching"


class WeightUnit(str, enum.Enum):
    KG = "kg"
    LB = "lb"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    oidc_subject = Column(String(255), unique=True, index=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    weight_unit = Column(SQLEnum(WeightUnit), default=WeightUnit.KG, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    routines = relationship("Routine", back_populates="owner", cascade="all, delete-orphan")
    workout_sessions = relationship("WorkoutSession", back_populates="user", cascade="all, delete-orphan")


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    body_part = Column(String(100), index=True, nullable=False)
    primary_muscles = Column(Text, nullable=False)
    secondary_muscles = Column(Text, nullable=True)
    equipment = Column(String(100), nullable=True)
    instructions = Column(Text, nullable=True)
    category = Column(SQLEnum(ExerciseCategory), default=ExerciseCategory.STRENGTH, nullable=False)
    weight_unit = Column(SQLEnum(WeightUnit), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    routine_exercises = relationship("RoutineExercise", back_populates="exercise")
    workout_entries = relationship("WorkoutEntry", back_populates="exercise")


class Routine(Base):
    __tablename__ = "routines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    phases = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="routines")
    exercises = relationship("RoutineExercise", back_populates="routine", cascade="all, delete-orphan", order_by="RoutineExercise.order")
    workout_sessions = relationship("WorkoutSession", back_populates="routine")


class RoutineExercise(Base):
    __tablename__ = "routine_exercises"

    id = Column(Integer, primary_key=True, index=True)
    routine_id = Column(Integer, ForeignKey("routines.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    order = Column(Integer, nullable=False, default=0)
    phase = Column(SQLEnum(RoutinePhase), default=RoutinePhase.WORK, nullable=False)
    sets = Column(Integer, nullable=False, default=3)
    target_reps = Column(String(50), nullable=True)
    target_rpe = Column(Integer, nullable=True)
    rest_seconds = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    routine = relationship("Routine", back_populates="exercises")
    exercise = relationship("Exercise", back_populates="routine_exercises")


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    routine_id = Column(Integer, ForeignKey("routines.id"), nullable=True)
    name = Column(String(255), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="workout_sessions")
    routine = relationship("Routine", back_populates="workout_sessions")
    entries = relationship("WorkoutEntry", back_populates="session", cascade="all, delete-orphan", order_by="WorkoutEntry.order")


class SetPhase(str, enum.Enum):
    WARMUP = "warmup"
    WORK = "work"


class WorkoutEntry(Base):
    __tablename__ = "workout_entries"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("workout_sessions.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    order = Column(Integer, nullable=False, default=0)
    phase = Column(SQLEnum(RoutinePhase), default=RoutinePhase.WORK, nullable=False)
    weight_unit = Column(SQLEnum(WeightUnit), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    session = relationship("WorkoutSession", back_populates="entries")
    exercise = relationship("Exercise", back_populates="workout_entries")
    sets = relationship("WorkoutSet", back_populates="entry", cascade="all, delete-orphan", order_by="WorkoutEntry.order")


class WorkoutSet(Base):
    __tablename__ = "workout_sets"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("workout_entries.id"), nullable=False)
    order = Column(Integer, nullable=False, default=0)
    set_phase = Column(SQLEnum(SetPhase), default=SetPhase.WORK, nullable=False)
    weight = Column(Integer, nullable=False)
    reps = Column(Integer, nullable=False)
    rpe = Column(Integer, nullable=True)
    completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    entry = relationship("WorkoutEntry", back_populates="sets")