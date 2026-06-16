"""
Fitness module models.

Exports all fitness-related SQLAlchemy models for workout tracking.
"""

from app.models.fitness.chat_message import ChatMessage, UserSession
from app.models.fitness.workout_log import (
    ExerciseResult,
    FeelingLevel,
    WorkoutLog,
)
from app.models.fitness.workout_plan import (
    DayExercise,
    DayWarmup,
    PlanDay,
    PlanWeek,
    WorkoutPlan,
    WorkoutStatus,
)
from app.models.fitness.profile import (
    InjuryStatus,
    InjuryEpisode,
    BloodMarker,
    BodyWeightLog,
)

__all__ = [
    # Enums
    "WorkoutStatus",
    "FeelingLevel",
    "InjuryStatus",
    # Workout Plan models
    "WorkoutPlan",
    "PlanWeek",
    "PlanDay",
    "DayWarmup",
    "DayExercise",
    # Workout Log models
    "WorkoutLog",
    "ExerciseResult",
    # Profile & Health
    "InjuryEpisode",
    "BloodMarker",
    "BodyWeightLog",
    # Chat & Sessions
    "ChatMessage",
    "UserSession",
]
