"""
Workout Log models for tracking completed workouts.

Schema:
- WorkoutLog: A completed workout session
- ExerciseResult: Actual performance vs planned for each exercise
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models import Base


class FeelingLevel(str, enum.Enum):
    """
    How the user felt during workout/exercise.

    Note: Use lowercase names to match PostgreSQL enum values.
    SQLAlchemy uses enum NAMES (not values) for DB serialization.
    """
    easy = "easy"
    normal = "normal"
    hard = "hard"
    exhausted = "exhausted"


class WorkoutLog(Base):
    """
    A completed workout session.
    Links to PlanDay to track which planned workout was performed.
    """
    __tablename__ = "workout_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    day_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plan_days.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    overall_feeling = Column(String(20), nullable=True)  # FeelingLevel value
    notes = Column(Text, nullable=True)
    synced = Column(Boolean, default=True)  # For offline PWA support
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    day = relationship("PlanDay", backref="workout_logs")
    exercise_results = relationship(
        "ExerciseResult",
        back_populates="workout_log",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_workout_logs_user_date", "user_id", "completed_at"),
        Index("ix_workout_logs_day", "day_id"),
    )

    def __repr__(self) -> str:
        return f"<WorkoutLog(id={self.id}, duration={self.duration_minutes}min)>"


class ExerciseResult(Base):
    """
    Actual performance for an exercise in a workout.
    Tracks planned vs actual sets, reps, and weight.
    """
    __tablename__ = "exercise_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workout_log_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workout_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id = Column(
        UUID(as_uuid=True),
        ForeignKey("day_exercises.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Planned values (copied from DayExercise at time of workout)
    planned_sets = Column(Integer, nullable=True)
    planned_reps = Column(String(50), nullable=True)
    planned_weight = Column(String(50), nullable=True)

    # Actual values (what user actually did)
    actual_sets = Column(Integer, nullable=True)
    actual_reps = Column(String(50), nullable=True)  # Could be "10,9,8" for drop-off
    actual_weight = Column(String(50), nullable=True)  # Could be "100,95,90" for drop sets

    # User feedback
    feeling = Column(String(20), nullable=True)  # FeelingLevel value
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    workout_log = relationship("WorkoutLog", back_populates="exercise_results")
    exercise = relationship("DayExercise", backref="results")

    __table_args__ = (
        Index("ix_exercise_results_log", "workout_log_id"),
        Index("ix_exercise_results_exercise", "exercise_id"),
    )

    def __repr__(self) -> str:
        return f"<ExerciseResult(id={self.id}, actual_sets={self.actual_sets})>"
