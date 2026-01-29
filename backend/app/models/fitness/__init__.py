"""
Fitness module models.

Exports all fitness-related SQLAlchemy models for workout tracking.
"""

from app.models.fitness.workout_plan import (
    WorkoutStatus,
    WorkoutPlan,
    PlanWeek,
    PlanDay,
    DayWarmup,
    DayExercise,
)
from app.models.fitness.workout_log import (
    FeelingLevel,
    WorkoutLog,
    ExerciseResult,
)
from app.models.fitness.chat_message import ChatMessage, UserSession

__all__ = [
    # Enums
    "WorkoutStatus",
    "FeelingLevel",
    # Workout Plan models
    "WorkoutPlan",
    "PlanWeek",
    "PlanDay",
    "DayWarmup",
    "DayExercise",
    # Workout Log models
    "WorkoutLog",
    "ExerciseResult",
    # Chat & Sessions
    "ChatMessage",
    "UserSession",
]
