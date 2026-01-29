"""
Workout Plan models for fitness tracking.

Schema:
- WorkoutPlan: Top-level plan (e.g., "Yates 12-Week Program")
- PlanWeek: Weekly breakdown
- PlanDay: Daily workout
- DayWarmup: Warmup instructions for a day
- DayExercise: Individual exercises for a day
"""

import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models import Base


class WorkoutStatus(str, enum.Enum):
    """
    Status for workout items (weeks, days, exercises).

    Note: Use lowercase names to match PostgreSQL enum values.
    SQLAlchemy uses enum NAMES (not values) for DB serialization.
    """
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"


class WorkoutPlan(Base):
    """
    Top-level workout plan.
    Example: "Dorian Yates 12-Week Blood & Guts Program"
    """
    __tablename__ = "workout_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    goal = Column(String(255), nullable=True)
    total_weeks = Column(Integer, nullable=False, default=12)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    weeks = relationship(
        "PlanWeek",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanWeek.week_number",
    )

    __table_args__ = (
        Index("ix_workout_plans_user_active", "user_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<WorkoutPlan(id={self.id}, name='{self.name}')>"


class PlanWeek(Base):
    """
    A week within a workout plan.
    """
    __tablename__ = "plan_weeks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workout_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    week_number = Column(Integer, nullable=False)
    status = Column(
        Enum(WorkoutStatus, name="workout_status"),
        default=WorkoutStatus.pending,
        nullable=False,
    )
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    plan = relationship("WorkoutPlan", back_populates="weeks")
    days = relationship(
        "PlanDay",
        back_populates="week",
        cascade="all, delete-orphan",
        order_by="PlanDay.day_number",
    )

    __table_args__ = (
        Index("ix_plan_weeks_plan_week", "plan_id", "week_number"),
    )

    def __repr__(self) -> str:
        return f"<PlanWeek(id={self.id}, week={self.week_number})>"


class PlanDay(Base):
    """
    A training day within a week.
    Example: "Day 1: Back & Biceps"
    """
    __tablename__ = "plan_days"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plan_weeks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_number = Column(Integer, nullable=False)
    name = Column(String(255), nullable=True)  # e.g., "Back & Biceps"
    status = Column(
        Enum(WorkoutStatus, name="workout_status", create_type=False),
        default=WorkoutStatus.pending,
        nullable=False,
    )
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    week = relationship("PlanWeek", back_populates="days")
    warmups = relationship(
        "DayWarmup",
        back_populates="day",
        cascade="all, delete-orphan",
    )
    exercises = relationship(
        "DayExercise",
        back_populates="day",
        cascade="all, delete-orphan",
        order_by="DayExercise.order_index",
    )

    __table_args__ = (
        Index("ix_plan_days_week_day", "week_id", "day_number"),
    )

    def __repr__(self) -> str:
        return f"<PlanDay(id={self.id}, day={self.day_number}, name='{self.name}')>"


class DayWarmup(Base):
    """
    Warmup instructions for a training day.
    """
    __tablename__ = "day_warmups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    day_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plan_days.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    instructions = Column(Text, nullable=False)
    comments = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    day = relationship("PlanDay", back_populates="warmups")

    def __repr__(self) -> str:
        return f"<DayWarmup(id={self.id}, duration={self.duration_minutes}min)>"


class DayExercise(Base):
    """
    An exercise within a training day.
    Example: "Barbell Row: 3x8-10 @ 100kg"
    """
    __tablename__ = "day_exercises"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    day_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plan_days.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    sets = Column(Integer, nullable=False, default=3)
    reps = Column(String(50), nullable=True)  # "8-10" or "12"
    weight = Column(String(50), nullable=True)  # "100kg" or "bodyweight"
    rest_seconds = Column(Integer, nullable=True, default=120)
    status = Column(
        Enum(WorkoutStatus, name="workout_status", create_type=False),
        default=WorkoutStatus.pending,
        nullable=False,
    )
    comments = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    day = relationship("PlanDay", back_populates="exercises")

    __table_args__ = (
        Index("ix_day_exercises_day_order", "day_id", "order_index"),
    )

    def __repr__(self) -> str:
        return f"<DayExercise(id={self.id}, name='{self.name}', sets={self.sets})>"
