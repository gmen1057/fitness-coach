"""
Universal MCP tool definitions and executor for fitness agent.

This module defines tools in a provider-agnostic format that can be used
with any LLM provider (Anthropic, OpenAI, xAI, etc.).
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.fitness import (
    WorkoutPlan,
    PlanWeek,
    PlanDay,
    DayExercise,
    WorkoutLog,
    ExerciseResult,
    WorkoutStatus,
)

logger = logging.getLogger(__name__)


# Universal tool definitions (provider-agnostic JSON schema)
TOOLS = [
    {
        "name": "get_workout_plans",
        "description": "Get all workout plans for the user. Returns list of plans with name, goal, and progress.",
        "parameters": {
            "type": "object",
            "properties": {
                "active_only": {
                    "type": "boolean",
                    "description": "If true, only return active plans",
                    "default": True
                }
            }
        }
    },
    {
        "name": "get_current_workout",
        "description": "Get the current or next scheduled workout for today. Returns workout details including exercises, warmups, and any previous notes.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_workout_stats",
        "description": "Get workout statistics and progress summary including total workouts, streak, and recent activity.",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back for statistics",
                    "default": 30
                }
            }
        }
    },
    {
        "name": "complete_workout_day",
        "description": "Mark a workout day as completed with optional results. Call this when user finishes their workout.",
        "parameters": {
            "type": "object",
            "properties": {
                "day_id": {
                    "type": "string",
                    "description": "UUID of the workout day to complete"
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "How long the workout took"
                },
                "feeling": {
                    "type": "string",
                    "description": "How the user felt during the workout"
                },
                "notes": {
                    "type": "string",
                    "description": "Any additional notes about the workout"
                },
                "exercise_results": {
                    "type": "array",
                    "description": "Detailed results for each exercise",
                    "items": {
                        "type": "object",
                        "properties": {
                            "exercise_id": {"type": "string"},
                            "actual_sets": {"type": "integer"},
                            "actual_reps": {"type": "string"},
                            "actual_weight": {"type": "string"},
                            "notes": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["day_id"]
        }
    },
    {
        "name": "skip_workout_day",
        "description": "Mark a workout day as skipped with a reason. Use when user can't do the workout.",
        "parameters": {
            "type": "object",
            "properties": {
                "day_id": {
                    "type": "string",
                    "description": "UUID of the workout day to skip"
                },
                "reason": {
                    "type": "string",
                    "description": "Why the workout is being skipped"
                }
            },
            "required": ["day_id", "reason"]
        }
    },
    {
        "name": "add_exercise_note",
        "description": "Add a note to a specific exercise in the plan. Useful for tracking form cues, weight adjustments, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "exercise_id": {
                    "type": "string",
                    "description": "UUID of the exercise"
                },
                "note": {
                    "type": "string",
                    "description": "Note to add to the exercise"
                }
            },
            "required": ["exercise_id", "note"]
        }
    },
    {
        "name": "create_workout_plan",
        "description": "Create a new workout plan. Use this when the user wants to start a new training program.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the workout plan"
                },
                "goal": {
                    "type": "string",
                    "description": "Goal of the workout plan (e.g., 'Build muscle', 'Lose weight')"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the plan"
                },
                "total_weeks": {
                    "type": "integer",
                    "description": "Total number of weeks in the plan",
                    "default": 12
                },
                "days_per_week": {
                    "type": "integer",
                    "description": "Number of training days per week",
                    "default": 4
                }
            },
            "required": ["name", "goal"]
        }
    },
    {
        "name": "update_workout_plan",
        "description": "Update an existing workout plan's details.",
        "parameters": {
            "type": "object",
            "properties": {
                "plan_id": {
                    "type": "string",
                    "description": "UUID of the workout plan to update"
                },
                "name": {
                    "type": "string",
                    "description": "New name for the plan"
                },
                "goal": {
                    "type": "string",
                    "description": "New goal for the plan"
                },
                "description": {
                    "type": "string",
                    "description": "New description"
                },
                "is_active": {
                    "type": "boolean",
                    "description": "Whether the plan is active"
                }
            },
            "required": ["plan_id"]
        }
    },
    {
        "name": "delete_workout_plan",
        "description": "Delete a workout plan and all its weeks, days, and exercises. This action is irreversible.",
        "parameters": {
            "type": "object",
            "properties": {
                "plan_id": {
                    "type": "string",
                    "description": "UUID of the workout plan to delete"
                }
            },
            "required": ["plan_id"]
        }
    },
    {
        "name": "get_plan_structure",
        "description": "Get the complete structure of a workout plan including all weeks, days, and exercises. Returns a full tree.",
        "parameters": {
            "type": "object",
            "properties": {
                "plan_id": {
                    "type": "string",
                    "description": "UUID of the workout plan"
                }
            },
            "required": ["plan_id"]
        }
    },
    {
        "name": "get_week_structure",
        "description": "Get a specific week with all its days and exercises. Use when user asks about a particular week.",
        "parameters": {
            "type": "object",
            "properties": {
                "week_id": {
                    "type": "string",
                    "description": "UUID of the week"
                }
            },
            "required": ["week_id"]
        }
    },
    {
        "name": "add_week_to_plan",
        "description": "Add a new week to an existing workout plan.",
        "parameters": {
            "type": "object",
            "properties": {
                "plan_id": {
                    "type": "string",
                    "description": "UUID of the workout plan"
                },
                "week_number": {
                    "type": "integer",
                    "description": "Week number (1, 2, 3, etc.)"
                }
            },
            "required": ["plan_id", "week_number"]
        }
    },
    {
        "name": "add_day_to_week",
        "description": "Add a training day to a week.",
        "parameters": {
            "type": "object",
            "properties": {
                "week_id": {
                    "type": "string",
                    "description": "UUID of the week"
                },
                "day_number": {
                    "type": "integer",
                    "description": "Day number within the week (1, 2, 3, etc.)"
                },
                "name": {
                    "type": "string",
                    "description": "Name of the training day (e.g., 'Push Day', 'Leg Day')"
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes for the day"
                }
            },
            "required": ["week_id", "day_number", "name"]
        }
    },
    {
        "name": "add_exercise_to_day",
        "description": "Add an exercise to a training day.",
        "parameters": {
            "type": "object",
            "properties": {
                "day_id": {
                    "type": "string",
                    "description": "UUID of the training day"
                },
                "name": {
                    "type": "string",
                    "description": "Name of the exercise"
                },
                "sets": {
                    "type": "integer",
                    "description": "Number of sets"
                },
                "reps": {
                    "type": "string",
                    "description": "Rep scheme (e.g., '8-12', '5x5', '6-8 each leg')"
                },
                "weight": {
                    "type": "string",
                    "description": "Weight to use (e.g., '45 kg', 'Bodyweight')"
                },
                "rest_seconds": {
                    "type": "integer",
                    "description": "Rest time between sets in seconds",
                    "default": 120
                },
                "comments": {
                    "type": "string",
                    "description": "Form cues or additional notes"
                },
                "order_index": {
                    "type": "integer",
                    "description": "Position in the exercise list (0 = first)",
                    "default": 0
                }
            },
            "required": ["day_id", "name", "sets", "reps"]
        }
    },
    {
        "name": "create_full_week",
        "description": "Create a complete week with all days and exercises in one call. Use this for efficient program creation instead of multiple add_day_to_week and add_exercise_to_day calls.",
        "parameters": {
            "type": "object",
            "properties": {
                "week_id": {
                    "type": "string",
                    "description": "UUID of the week to populate"
                },
                "days": {
                    "type": "array",
                    "description": "Array of days with their exercises",
                    "items": {
                        "type": "object",
                        "properties": {
                            "day_number": {"type": "integer"},
                            "name": {"type": "string"},
                            "notes": {"type": "string"},
                            "exercises": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "sets": {"type": "integer"},
                                        "reps": {"type": "string"},
                                        "weight": {"type": "string"},
                                        "rest_seconds": {"type": "integer"},
                                        "comments": {"type": "string"}
                                    },
                                    "required": ["name", "sets", "reps"]
                                }
                            }
                        },
                        "required": ["day_number", "name"]
                    }
                }
            },
            "required": ["week_id", "days"]
        }
    },
    {
        "name": "create_full_plan",
        "description": "Create a complete workout plan with all weeks, days, and exercises in ONE database transaction. This is the MOST EFFICIENT way to create a training program - use this instead of create_workout_plan + add_week_to_plan + add_day_to_week + add_exercise_to_day calls.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the workout plan"
                },
                "goal": {
                    "type": "string",
                    "description": "Goal of the workout plan (e.g., 'Build muscle', 'Lose weight')"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the plan"
                },
                "weeks": {
                    "type": "array",
                    "description": "Array of weeks with their days and exercises",
                    "items": {
                        "type": "object",
                        "properties": {
                            "week_number": {"type": "integer"},
                            "name": {"type": "string"},
                            "days": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "day_number": {"type": "integer"},
                                        "name": {"type": "string"},
                                        "notes": {"type": "string"},
                                        "exercises": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "name": {"type": "string"},
                                                    "sets": {"type": "integer"},
                                                    "reps": {"type": "string"},
                                                    "weight": {"type": "string"},
                                                    "rest_seconds": {"type": "integer"},
                                                    "comments": {"type": "string"}
                                                },
                                                "required": ["name", "sets", "reps"]
                                            }
                                        }
                                    },
                                    "required": ["day_number", "name"]
                                }
                            }
                        },
                        "required": ["week_number", "days"]
                    }
                }
            },
            "required": ["name", "goal", "weeks"]
        }
    },
    {
        "name": "update_exercise",
        "description": "Update an existing exercise's details.",
        "parameters": {
            "type": "object",
            "properties": {
                "exercise_id": {
                    "type": "string",
                    "description": "UUID of the exercise to update"
                },
                "name": {
                    "type": "string",
                    "description": "New name for the exercise"
                },
                "sets": {
                    "type": "integer",
                    "description": "New number of sets"
                },
                "reps": {
                    "type": "string",
                    "description": "New rep scheme"
                },
                "weight": {
                    "type": "string",
                    "description": "New weight"
                },
                "rest_seconds": {
                    "type": "integer",
                    "description": "New rest time"
                },
                "comments": {
                    "type": "string",
                    "description": "New comments"
                }
            },
            "required": ["exercise_id"]
        }
    },
    {
        "name": "bulk_update_exercises",
        "description": "Update multiple exercises in one call. Much more efficient than calling update_exercise multiple times.",
        "parameters": {
            "type": "object",
            "properties": {
                "updates": {
                    "type": "array",
                    "description": "Array of exercise updates",
                    "items": {
                        "type": "object",
                        "properties": {
                            "exercise_id": {"type": "string"},
                            "name": {"type": "string"},
                            "sets": {"type": "integer"},
                            "reps": {"type": "string"},
                            "weight": {"type": "string"},
                            "rest_seconds": {"type": "integer"},
                            "comments": {"type": "string"}
                        },
                        "required": ["exercise_id"]
                    }
                }
            },
            "required": ["updates"]
        }
    },
    {
        "name": "delete_exercise",
        "description": "Delete an exercise from a training day.",
        "parameters": {
            "type": "object",
            "properties": {
                "exercise_id": {
                    "type": "string",
                    "description": "UUID of the exercise to delete"
                }
            },
            "required": ["exercise_id"]
        }
    },
    {
        "name": "mark_day_status",
        "description": "Change the status of a training day.",
        "parameters": {
            "type": "object",
            "properties": {
                "day_id": {
                    "type": "string",
                    "description": "UUID of the training day"
                },
                "status": {
                    "type": "string",
                    "description": "New status: pending, in_progress, completed, or skipped"
                }
            },
            "required": ["day_id", "status"]
        }
    },
    {
        "name": "delete_day_from_week",
        "description": "Delete a specific training day from a week. Use when user wants to remove a day without deleting the whole plan.",
        "parameters": {
            "type": "object",
            "properties": {
                "day_id": {
                    "type": "string",
                    "description": "UUID of the day to delete"
                }
            },
            "required": ["day_id"]
        }
    },
    {
        "name": "search_workout_memory",
        "description": "Search through workout history and fitness knowledge using semantic similarity. Use to find relevant past workouts, exercises, or fitness insights based on meaning, not just keywords.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query (e.g., 'back exercises I did last month', 'high intensity leg workouts')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "store_fitness_insight",
        "description": "Store important fitness insight, preference, or note for future reference. Use when user shares something worth remembering (injury, preference, goal, achievement).",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The insight or note to store"
                },
                "category": {
                    "type": "string",
                    "enum": ["preference", "injury", "goal", "achievement", "note"],
                    "description": "Category of the insight"
                }
            },
            "required": ["content", "category"]
        }
    },
    {
        "name": "get_exercise_alternatives",
        "description": "Find alternative exercises that work the same muscle groups. Use when user can't do an exercise or wants variety.",
        "parameters": {
            "type": "object",
            "properties": {
                "exercise_name": {
                    "type": "string",
                    "description": "Name of the exercise to find alternatives for"
                }
            },
            "required": ["exercise_name"]
        }
    },
    {
        "name": "get_exercise_progression",
        "description": "Get the progression path for an exercise (easier → harder variations).",
        "parameters": {
            "type": "object",
            "properties": {
                "exercise_name": {
                    "type": "string",
                    "description": "Name of the exercise"
                }
            },
            "required": ["exercise_name"]
        }
    },
    {
        "name": "get_muscles_for_exercise",
        "description": "Get which muscle groups an exercise targets (primary and secondary).",
        "parameters": {
            "type": "object",
            "properties": {
                "exercise_name": {
                    "type": "string",
                    "description": "Name of the exercise"
                }
            },
            "required": ["exercise_name"]
        }
    },
    {
        "name": "get_exercises_for_muscle",
        "description": "Find exercises that target a specific muscle group.",
        "parameters": {
            "type": "object",
            "properties": {
                "muscle_group": {
                    "type": "string",
                    "description": "Muscle group (e.g., 'chest', 'back', 'legs', 'shoulders', 'biceps', 'triceps', 'core')"
                }
            },
            "required": ["muscle_group"]
        }
    }
]


class ToolExecutor:
    """
    Executes MCP tools against the database.

    This class provides a provider-agnostic interface for executing tools.
    It takes tool name and arguments, executes the tool, and returns results.
    """

    def __init__(self, db: AsyncSession, user_id: UUID):
        """
        Initialize tool executor.

        Args:
            db: Database session
            user_id: User ID for filtering data
        """
        self.db = db
        self.user_id = user_id

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments

        Returns:
            Tool result as dictionary
        """
        # Map tool names to handler methods
        handlers = {
            "get_workout_plans": self._get_workout_plans,
            "get_current_workout": self._get_current_workout,
            "get_workout_stats": self._get_workout_stats,
            "complete_workout_day": self._complete_workout_day,
            "skip_workout_day": self._skip_workout_day,
            "add_exercise_note": self._add_exercise_note,
            "create_workout_plan": self._create_workout_plan,
            "update_workout_plan": self._update_workout_plan,
            "delete_workout_plan": self._delete_workout_plan,
            "get_plan_structure": self._get_plan_structure,
            "get_week_structure": self._get_week_structure,
            "add_week_to_plan": self._add_week_to_plan,
            "add_day_to_week": self._add_day_to_week,
            "add_exercise_to_day": self._add_exercise_to_day,
            "create_full_week": self._create_full_week,
            "create_full_plan": self._create_full_plan,
            "update_exercise": self._update_exercise,
            "bulk_update_exercises": self._bulk_update_exercises,
            "delete_exercise": self._delete_exercise,
            "mark_day_status": self._mark_day_status,
            "delete_day_from_week": self._delete_day_from_week,
            "search_workout_memory": self._search_workout_memory,
            "store_fitness_insight": self._store_fitness_insight,
            "get_exercise_alternatives": self._get_exercise_alternatives,
            "get_exercise_progression": self._get_exercise_progression,
            "get_muscles_for_exercise": self._get_muscles_for_exercise,
            "get_exercises_for_muscle": self._get_exercises_for_muscle,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}

        logger.info(f"Executing tool {tool_name} with args: {args}")

        try:
            return await handler(args)
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            return {"error": str(e)}

    async def _get_workout_plans(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get all workout plans for the user"""
        active_only = args.get("active_only", True)

        query = (
            select(WorkoutPlan)
            .where(WorkoutPlan.user_id == self.user_id)
            .options(
                selectinload(WorkoutPlan.weeks).selectinload(PlanWeek.days)
            )
            .order_by(WorkoutPlan.created_at.desc())
        )

        if active_only:
            query = query.where(WorkoutPlan.is_active == True)

        result = await self.db.execute(query)
        plans = result.scalars().all()

        if not plans:
            return {
                "plans": [],
                "message": "No workout plans found. Would you like me to help you create one?"
            }

        plans_data = []
        for plan in plans:
            total_days = sum(len(week.days) for week in plan.weeks)
            completed_days = sum(
                1 for week in plan.weeks
                for day in week.days
                if day.status == WorkoutStatus.completed
            )

            plans_data.append({
                "id": str(plan.id),
                "name": plan.name,
                "goal": plan.goal,
                "description": plan.description,
                "total_weeks": plan.total_weeks,
                "is_active": plan.is_active,
                "progress": {
                    "total_days": total_days,
                    "completed_days": completed_days,
                    "percentage": round(completed_days / total_days * 100, 1) if total_days > 0 else 0
                }
            })

        return {"plans": plans_data}

    async def _get_current_workout(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get today's or next pending workout"""
        plan_query = (
            select(WorkoutPlan)
            .where(
                and_(
                    WorkoutPlan.user_id == self.user_id,
                    WorkoutPlan.is_active == True
                )
            )
            .options(
                selectinload(WorkoutPlan.weeks)
                .selectinload(PlanWeek.days)
                .selectinload(PlanDay.exercises)
            )
        )
        result = await self.db.execute(plan_query)
        plan = result.scalar_one_or_none()

        if not plan:
            return {
                "workout": None,
                "message": "No active workout plan found. Would you like to create one?"
            }

        # Find next pending day
        for week in sorted(plan.weeks, key=lambda w: w.week_number):
            for day in sorted(week.days, key=lambda d: d.day_number):
                if day.status in (WorkoutStatus.pending, WorkoutStatus.in_progress):
                    workout_data = {
                        "workout": {
                            "plan_name": plan.name,
                            "week_number": week.week_number,
                            "day_number": day.day_number,
                            "day_id": str(day.id),
                            "name": day.name,
                            "status": day.status.value,
                            "notes": day.notes,
                            "exercises": [
                                {
                                    "id": str(ex.id),
                                    "name": ex.name,
                                    "sets": ex.sets,
                                    "reps": ex.reps,
                                    "weight": ex.weight,
                                    "rest_seconds": ex.rest_seconds,
                                    "comments": ex.comments,
                                    "status": ex.status.value
                                }
                                for ex in sorted(day.exercises, key=lambda e: e.order_index)
                            ]
                        }
                    }
                    return workout_data

        return {
            "workout": None,
            "message": "All workouts in the current plan are completed! Great job!"
        }

    async def _get_workout_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get workout statistics and progress"""
        days = args.get("days", 30)
        since_date = datetime.utcnow() - timedelta(days=days)

        # Count completed workouts in period
        completed_query = (
            select(func.count(WorkoutLog.id))
            .where(
                and_(
                    WorkoutLog.user_id == self.user_id,
                    WorkoutLog.completed_at >= since_date,
                    WorkoutLog.completed_at.isnot(None)
                )
            )
        )
        completed_result = await self.db.execute(completed_query)
        completed_count = completed_result.scalar() or 0

        # Total workout time
        duration_query = (
            select(func.sum(WorkoutLog.duration_minutes))
            .where(
                and_(
                    WorkoutLog.user_id == self.user_id,
                    WorkoutLog.completed_at >= since_date
                )
            )
        )
        duration_result = await self.db.execute(duration_query)
        total_minutes = duration_result.scalar() or 0

        # Get streak
        streak_query = (
            select(WorkoutLog.completed_at)
            .where(
                and_(
                    WorkoutLog.user_id == self.user_id,
                    WorkoutLog.completed_at.isnot(None)
                )
            )
            .order_by(WorkoutLog.completed_at.desc())
            .limit(30)
        )
        streak_result = await self.db.execute(streak_query)
        workout_dates = [row[0].date() for row in streak_result.all() if row[0]]

        streak = 0
        if workout_dates:
            today = datetime.utcnow().date()
            check_date = today
            for _ in range(len(workout_dates)):
                if check_date in workout_dates or (check_date - timedelta(days=1)) in workout_dates:
                    streak += 1
                    check_date -= timedelta(days=1)
                else:
                    break

        # Recent workouts
        recent_query = (
            select(WorkoutLog)
            .where(WorkoutLog.user_id == self.user_id)
            .order_by(WorkoutLog.completed_at.desc())
            .limit(5)
        )
        recent_result = await self.db.execute(recent_query)
        recent_logs = recent_result.scalars().all()

        stats_data = {
            "period_days": days,
            "completed_workouts": completed_count,
            "total_minutes": total_minutes,
            "average_duration": round(total_minutes / completed_count) if completed_count > 0 else 0,
            "current_streak": streak,
            "recent_workouts": [
                {
                    "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                    "duration_minutes": log.duration_minutes,
                    "feeling": log.overall_feeling,
                    "notes": log.notes
                }
                for log in recent_logs
            ]
        }

        return stats_data

    async def _complete_workout_day(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Mark a workout day as completed"""
        day_id = args.get("day_id")
        duration_minutes = args.get("duration_minutes")
        feeling = args.get("feeling")
        notes = args.get("notes")
        exercise_results = args.get("exercise_results")

        if not day_id:
            return {"error": "day_id is required"}

        try:
            day_uuid = UUID(day_id) if isinstance(day_id, str) else day_id
        except (ValueError, TypeError):
            return {"error": f"Invalid day_id format: {day_id}"}

        # Get the day
        day_query = (
            select(PlanDay)
            .where(PlanDay.id == day_uuid)
            .options(selectinload(PlanDay.exercises))
        )
        result = await self.db.execute(day_query)
        day = result.scalar_one_or_none()

        if not day:
            return {"error": f"Workout day {day_id} not found"}

        # Update day status
        day.status = WorkoutStatus.completed
        day.notes = notes if notes else day.notes

        # Create workout log
        log = WorkoutLog(
            user_id=self.user_id,
            day_id=day_uuid,
            completed_at=datetime.utcnow(),
            duration_minutes=duration_minutes,
            overall_feeling=feeling,
            notes=notes
        )
        self.db.add(log)

        # Add exercise results if provided, otherwise copy planned values
        if exercise_results:
            for ex_result in exercise_results:
                exercise_id_str = ex_result.get("exercise_id")
                exercise_id_uuid = None
                if exercise_id_str:
                    try:
                        exercise_id_uuid = UUID(exercise_id_str) if isinstance(exercise_id_str, str) else exercise_id_str
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid exercise_id format in result: {exercise_id_str}")

                exercise = ExerciseResult(
                    workout_log=log,
                    exercise_id=exercise_id_uuid,
                    actual_sets=ex_result.get("actual_sets"),
                    actual_reps=ex_result.get("actual_reps"),
                    actual_weight=ex_result.get("actual_weight"),
                    notes=ex_result.get("notes")
                )
                self.db.add(exercise)
        else:
            # Auto-copy planned weights from day_exercises for progress tracking
            for planned_ex in day.exercises:
                # Skip warmups and exercises without numeric weight
                if planned_ex.weight and planned_ex.weight not in ['-', 'Своё тело', 'Своє тіло']:
                    exercise = ExerciseResult(
                        workout_log=log,
                        exercise_id=planned_ex.id,
                        actual_sets=planned_ex.sets,
                        actual_reps=planned_ex.reps,
                        actual_weight=planned_ex.weight,
                        notes=None
                    )
                    self.db.add(exercise)

        await self.db.commit()

        # Index completion for RAG (non-blocking)
        try:
            from app.services.rag_indexer import index_completed_workout
            await index_completed_workout(self.db, day_uuid, self.user_id, duration_minutes)
        except Exception as e:
            logger.warning(f"RAG indexing failed (non-critical): {e}")

        return {
            "success": True,
            "message": f"Workout '{day.name}' marked as completed!",
            "workout_log_id": str(log.id),
            "day_name": day.name
        }

    async def _skip_workout_day(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Mark a workout day as skipped"""
        day_id = args.get("day_id")
        reason = args.get("reason")

        if not day_id:
            return {"error": "day_id is required"}

        try:
            day_uuid = UUID(day_id) if isinstance(day_id, str) else day_id
        except (ValueError, TypeError):
            return {"error": f"Invalid day_id format: {day_id}"}

        # Get the day
        day_query = select(PlanDay).where(PlanDay.id == day_uuid)
        result = await self.db.execute(day_query)
        day = result.scalar_one_or_none()

        if not day:
            return {"error": f"Workout day {day_id} not found"}

        # Update status
        day.status = WorkoutStatus.skipped
        day.notes = f"Skipped: {reason}" + (f"\n{day.notes}" if day.notes else "")

        await self.db.commit()

        return {
            "success": True,
            "message": f"Workout '{day.name}' marked as skipped.",
            "reason": reason,
            "day_name": day.name
        }

    async def _add_exercise_note(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add a note to an exercise"""
        exercise_id = args.get("exercise_id")
        note = args.get("note")

        if not exercise_id:
            return {"error": "exercise_id is required"}

        try:
            exercise_uuid = UUID(exercise_id) if isinstance(exercise_id, str) else exercise_id
        except (ValueError, TypeError):
            return {"error": f"Invalid exercise_id format: {exercise_id}"}

        exercise_query = select(DayExercise).where(DayExercise.id == exercise_uuid)
        result = await self.db.execute(exercise_query)
        exercise = result.scalar_one_or_none()

        if not exercise:
            return {"error": f"Exercise {exercise_id} not found"}

        # Append note
        if exercise.comments:
            exercise.comments = f"{exercise.comments}\n{datetime.utcnow().strftime('%Y-%m-%d')}: {note}"
        else:
            exercise.comments = f"{datetime.utcnow().strftime('%Y-%m-%d')}: {note}"

        await self.db.commit()

        return {
            "success": True,
            "message": f"Note added to '{exercise.name}'",
            "exercise_name": exercise.name
        }

    async def _create_workout_plan(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workout plan"""
        name = args.get("name")
        goal = args.get("goal")
        description = args.get("description")
        total_weeks = args.get("total_weeks", 12)
        days_per_week = args.get("days_per_week", 4)

        # Validate required fields
        if not name:
            return {"error": "Plan name is required. Please provide a name for the workout plan."}
        if not goal:
            return {"error": "Plan goal is required. Please provide a goal (e.g., 'Build muscle', 'Lose weight')."}

        plan = WorkoutPlan(
            user_id=self.user_id,
            name=name,
            goal=goal,
            description=description,
            total_weeks=total_weeks,
            is_active=True
        )
        self.db.add(plan)
        await self.db.flush()
        await self.db.commit()

        # Index for RAG (non-blocking)
        try:
            from app.services.rag_indexer import index_workout_plan
            await index_workout_plan(self.db, plan.id, self.user_id)
        except Exception as e:
            logger.warning(f"RAG indexing failed (non-critical): {e}")

        return {
            "success": True,
            "plan_id": str(plan.id),
            "message": f"Created workout plan '{name}' with goal '{goal}'",
            "total_weeks": total_weeks,
            "days_per_week": days_per_week,
            "hint": "Use add_week_to_plan and add_day_to_week to build the plan structure"
        }

    async def _create_full_plan(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a complete workout plan with all weeks, days, and exercises.

        This is the most efficient way to create a training program -
        everything in ONE database transaction.
        """
        name = args.get("name")
        goal = args.get("goal")
        description = args.get("description")
        weeks_data = args.get("weeks", [])

        # Validate required fields
        if not name:
            return {"error": "Plan name is required"}
        if not goal:
            return {"error": "Plan goal is required"}
        if not weeks_data:
            return {"error": "At least one week is required"}

        try:
            # Create plan
            plan = WorkoutPlan(
                user_id=self.user_id,
                name=name,
                goal=goal,
                description=description,
                total_weeks=len(weeks_data),
                is_active=True
            )
            self.db.add(plan)
            await self.db.flush()

            total_days = 0
            total_exercises = 0

            # Create all weeks, days, and exercises
            for week_data in weeks_data:
                week = PlanWeek(
                    plan_id=plan.id,
                    week_number=week_data.get("week_number", 1),
                    # Note: PlanWeek doesn't have 'name' field, only week_number
                    status=WorkoutStatus.pending
                )
                self.db.add(week)
                await self.db.flush()

                for day_data in week_data.get("days", []):
                    day = PlanDay(
                        week_id=week.id,
                        day_number=day_data.get("day_number", 1),
                        name=day_data.get("name", f"Day {day_data.get('day_number', 1)}"),
                        notes=day_data.get("notes"),
                        status=WorkoutStatus.pending
                    )
                    self.db.add(day)
                    await self.db.flush()
                    total_days += 1

                    for i, ex_data in enumerate(day_data.get("exercises", [])):
                        exercise = DayExercise(
                            day_id=day.id,
                            order_index=i,
                            name=ex_data.get("name"),
                            sets=ex_data.get("sets", 3),
                            reps=ex_data.get("reps", "10"),
                            weight=ex_data.get("weight"),
                            rest_seconds=ex_data.get("rest_seconds", 90),
                            comments=ex_data.get("comments"),
                            status=WorkoutStatus.pending
                        )
                        self.db.add(exercise)
                        total_exercises += 1

            await self.db.commit()

            # Index for RAG (non-blocking)
            try:
                from app.services.rag_indexer import index_workout_plan
                await index_workout_plan(self.db, plan.id, self.user_id)
            except Exception as e:
                logger.warning(f"RAG indexing failed (non-critical): {e}")

            return {
                "success": True,
                "plan_id": str(plan.id),
                "message": f"Created complete plan '{name}' with {len(weeks_data)} weeks, {total_days} days, {total_exercises} exercises",
                "summary": {
                    "weeks": len(weeks_data),
                    "days": total_days,
                    "exercises": total_exercises
                }
            }

        except Exception as e:
            logger.error(f"Failed to create full plan: {e}", exc_info=True)
            await self.db.rollback()
            return {"error": f"Failed to create plan: {str(e)}"}

    async def _update_workout_plan(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing workout plan"""
        plan_id = args.get("plan_id")
        name = args.get("name")
        goal = args.get("goal")
        description = args.get("description")
        is_active = args.get("is_active")

        if not plan_id:
            return {"error": "plan_id is required"}

        try:
            plan_uuid = UUID(plan_id) if isinstance(plan_id, str) else plan_id
        except (ValueError, TypeError):
            return {"error": f"Invalid plan_id format: {plan_id}"}

        query = select(WorkoutPlan).where(
            and_(
                WorkoutPlan.id == plan_uuid,
                WorkoutPlan.user_id == self.user_id
            )
        )
        result = await self.db.execute(query)
        plan = result.scalar_one_or_none()

        if not plan:
            return {"error": f"Workout plan {plan_id} not found"}

        # Update fields if provided
        if name is not None:
            plan.name = name
        if goal is not None:
            plan.goal = goal
        if description is not None:
            plan.description = description
        if is_active is not None:
            plan.is_active = is_active

        await self.db.commit()

        return {
            "success": True,
            "message": f"Updated workout plan '{plan.name}'",
            "plan_id": str(plan.id)
        }

    async def _delete_workout_plan(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a workout plan and all its contents"""
        logger.info(f"delete_workout_plan args: {args}")
        plan_id = args.get("plan_id")
        logger.info(f"plan_id: {plan_id!r}, type: {type(plan_id)}")

        if not plan_id:
            logger.warning(f"plan_id is falsy: {plan_id!r}")
            return {"error": "plan_id is required"}

        try:
            plan_uuid = UUID(plan_id) if isinstance(plan_id, str) else plan_id
        except (ValueError, TypeError):
            return {"error": f"Invalid plan_id format: {plan_id}"}

        query = select(WorkoutPlan).where(
            and_(
                WorkoutPlan.id == plan_uuid,
                WorkoutPlan.user_id == self.user_id
            )
        )
        result = await self.db.execute(query)
        plan = result.scalar_one_or_none()

        if not plan:
            return {"error": f"Workout plan {plan_id} not found"}

        plan_name = plan.name
        await self.db.delete(plan)
        await self.db.commit()

        return {
            "success": True,
            "message": f"Deleted workout plan '{plan_name}' and all associated data"
        }

    async def _get_plan_structure(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get complete plan structure with weeks, days, and exercises"""
        plan_id = args.get("plan_id")

        if not plan_id:
            return {"error": "plan_id is required"}

        try:
            plan_uuid = UUID(plan_id) if isinstance(plan_id, str) else plan_id
        except (ValueError, TypeError):
            return {"error": f"Invalid plan_id format: {plan_id}"}

        query = (
            select(WorkoutPlan)
            .where(
                and_(
                    WorkoutPlan.id == plan_uuid,
                    WorkoutPlan.user_id == self.user_id
                )
            )
            .options(
                selectinload(WorkoutPlan.weeks)
                .selectinload(PlanWeek.days)
                .selectinload(PlanDay.exercises)
            )
        )
        result = await self.db.execute(query)
        plan = result.scalar_one_or_none()

        if not plan:
            return {"error": f"Workout plan {plan_id} not found"}

        # Build full tree structure
        weeks_data = []
        for week in sorted(plan.weeks, key=lambda w: w.week_number):
            days_data = []
            for day in sorted(week.days, key=lambda d: d.day_number):
                exercises_data = [
                    {
                        "id": str(ex.id),
                        "name": ex.name,
                        "sets": ex.sets,
                        "reps": ex.reps,
                        "weight": ex.weight,
                        "rest_seconds": ex.rest_seconds,
                        "status": ex.status.value,
                        "comments": ex.comments,
                        "order_index": ex.order_index
                    }
                    for ex in sorted(day.exercises, key=lambda e: e.order_index)
                ]
                days_data.append({
                    "id": str(day.id),
                    "day_number": day.day_number,
                    "name": day.name,
                    "status": day.status.value,
                    "notes": day.notes,
                    "exercises": exercises_data
                })
            weeks_data.append({
                "id": str(week.id),
                "week_number": week.week_number,
                "status": week.status.value,
                "notes": week.notes,
                "days": days_data
            })

        return {
            "plan": {
                "id": str(plan.id),
                "name": plan.name,
                "goal": plan.goal,
                "description": plan.description,
                "total_weeks": plan.total_weeks,
                "is_active": plan.is_active,
                "weeks": weeks_data
            }
        }

    async def _get_week_structure(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get week structure with all days and exercises"""
        week_id = args.get("week_id")

        if not week_id:
            return {"error": "week_id is required"}

        try:
            week_uuid = UUID(week_id) if isinstance(week_id, str) else week_id
        except (ValueError, TypeError):
            return {"error": f"Invalid week_id format: {week_id}"}

        query = (
            select(PlanWeek)
            .where(PlanWeek.id == week_uuid)
            .options(
                selectinload(PlanWeek.days)
                .selectinload(PlanDay.exercises)
            )
        )
        result = await self.db.execute(query)
        week = result.scalar_one_or_none()

        if not week:
            return {"error": f"Week {week_id} not found"}

        days_data = []
        for day in sorted(week.days, key=lambda d: d.day_number):
            exercises_data = [
                {
                    "id": str(ex.id),
                    "name": ex.name,
                    "sets": ex.sets,
                    "reps": ex.reps,
                    "weight": ex.weight,
                    "rest_seconds": ex.rest_seconds,
                    "status": ex.status.value,
                    "comments": ex.comments
                }
                for ex in sorted(day.exercises, key=lambda e: e.order_index)
            ]
            days_data.append({
                "id": str(day.id),
                "day_number": day.day_number,
                "name": day.name,
                "status": day.status.value,
                "notes": day.notes,
                "exercises": exercises_data
            })

        return {
            "week": {
                "id": str(week.id),
                "week_number": week.week_number,
                "status": week.status.value,
                "notes": week.notes,
                "days": days_data
            }
        }

    async def _add_week_to_plan(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new week to a workout plan"""
        plan_id = args.get("plan_id")
        week_number = args.get("week_number")

        if not plan_id:
            return {"error": "plan_id is required"}
        if not week_number:
            return {"error": "week_number is required"}

        try:
            plan_uuid = UUID(plan_id) if isinstance(plan_id, str) else plan_id
        except (ValueError, TypeError):
            return {"error": f"Invalid plan_id format: {plan_id}"}

        # Verify plan exists and belongs to user
        plan_query = select(WorkoutPlan).where(
            and_(
                WorkoutPlan.id == plan_uuid,
                WorkoutPlan.user_id == self.user_id
            )
        )
        result = await self.db.execute(plan_query)
        plan = result.scalar_one_or_none()

        if not plan:
            return {"error": f"Workout plan {plan_id} not found"}

        # Check if week already exists
        existing_query = select(PlanWeek).where(
            and_(
                PlanWeek.plan_id == plan_uuid,
                PlanWeek.week_number == week_number
            )
        )
        existing_result = await self.db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            return {"error": f"Week {week_number} already exists in this plan"}

        week = PlanWeek(
            plan_id=plan_uuid,
            week_number=week_number,
            status=WorkoutStatus.pending
        )
        self.db.add(week)
        await self.db.commit()

        return {
            "success": True,
            "week_id": str(week.id),
            "message": f"Added week {week_number} to plan '{plan.name}'",
            "week_number": week_number
        }

    async def _add_day_to_week(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add a training day to a week"""
        week_id = args.get("week_id")
        day_number = args.get("day_number")
        name = args.get("name")
        notes = args.get("notes")

        if not week_id:
            return {"error": "week_id is required"}
        if not day_number:
            return {"error": "day_number is required"}

        try:
            week_uuid = UUID(week_id) if isinstance(week_id, str) else week_id
        except (ValueError, TypeError):
            return {"error": f"Invalid week_id format: {week_id}"}

        # Verify week exists
        week_query = select(PlanWeek).where(PlanWeek.id == week_uuid)
        result = await self.db.execute(week_query)
        week = result.scalar_one_or_none()

        if not week:
            return {"error": f"Week {week_id} not found"}

        # Check if day already exists
        existing_query = select(PlanDay).where(
            and_(
                PlanDay.week_id == week_uuid,
                PlanDay.day_number == day_number
            )
        )
        existing_result = await self.db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            return {"error": f"Day {day_number} already exists in this week"}

        day = PlanDay(
            week_id=week_uuid,
            day_number=day_number,
            name=name,
            notes=notes,
            status=WorkoutStatus.pending
        )
        self.db.add(day)
        await self.db.commit()

        return {
            "success": True,
            "day_id": str(day.id),
            "message": f"Added day {day_number} '{name}' to week {week.week_number}",
            "day_number": day_number,
            "name": name
        }

    async def _add_exercise_to_day(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add an exercise to a training day"""
        day_id = args.get("day_id")
        name = args.get("name")
        sets = args.get("sets")
        reps = args.get("reps")
        weight = args.get("weight")
        rest_seconds = args.get("rest_seconds", 120)
        comments = args.get("comments")
        order_index = args.get("order_index", 0)

        if not day_id:
            return {"error": "day_id is required"}
        if not name:
            return {"error": "Exercise name is required"}

        try:
            day_uuid = UUID(day_id) if isinstance(day_id, str) else day_id
        except (ValueError, TypeError):
            return {"error": f"Invalid day_id format: {day_id}"}

        # Verify day exists
        day_query = select(PlanDay).where(PlanDay.id == day_uuid)
        result = await self.db.execute(day_query)
        day = result.scalar_one_or_none()

        if not day:
            return {"error": f"Training day {day_id} not found"}

        # Get max order_index if not specified
        if order_index == 0:
            max_order_query = (
                select(func.max(DayExercise.order_index))
                .where(DayExercise.day_id == day_uuid)
            )
            max_result = await self.db.execute(max_order_query)
            max_order = max_result.scalar()
            order_index = (max_order or -1) + 1

        exercise = DayExercise(
            day_id=day_uuid,
            name=name,
            sets=sets,
            reps=reps,
            weight=weight,
            rest_seconds=rest_seconds,
            comments=comments,
            order_index=order_index,
            status=WorkoutStatus.pending
        )
        self.db.add(exercise)
        await self.db.commit()

        return {
            "success": True,
            "exercise_id": str(exercise.id),
            "message": f"Added '{name}' ({sets}x{reps}) to '{day.name}'"
        }

    async def _create_full_week(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a complete week with all days and exercises in one transaction."""
        week_id = args.get("week_id")
        days_data = args.get("days", [])

        if not week_id:
            return {"error": "week_id is required"}

        try:
            week_uuid = UUID(week_id) if isinstance(week_id, str) else week_id
        except (ValueError, TypeError):
            return {"error": f"Invalid week_id format: {week_id}"}

        # Verify week exists
        week_query = select(PlanWeek).where(PlanWeek.id == week_uuid)
        result = await self.db.execute(week_query)
        week = result.scalar_one_or_none()

        if not week:
            return {"error": f"Week {week_id} not found"}

        created_days = []
        total_exercises = 0

        for day_info in days_data:
            day_number = day_info.get("day_number")
            day_name = day_info.get("name")
            day_notes = day_info.get("notes")
            exercises = day_info.get("exercises", [])

            # Check if day already exists
            existing_query = select(PlanDay).where(
                and_(
                    PlanDay.week_id == week_uuid,
                    PlanDay.day_number == day_number
                )
            )
            existing_result = await self.db.execute(existing_query)
            if existing_result.scalar_one_or_none():
                continue  # Skip existing days

            # Create day
            day = PlanDay(
                week_id=week_uuid,
                day_number=day_number,
                name=day_name,
                notes=day_notes,
                status=WorkoutStatus.pending
            )
            self.db.add(day)
            await self.db.flush()  # Get day.id without committing

            # Create exercises for this day
            for idx, ex_data in enumerate(exercises):
                exercise = DayExercise(
                    day_id=day.id,
                    name=ex_data.get("name"),
                    sets=ex_data.get("sets", 3),
                    reps=ex_data.get("reps", "8-12"),
                    weight=ex_data.get("weight"),
                    rest_seconds=ex_data.get("rest_seconds", 120),
                    comments=ex_data.get("comments"),
                    order_index=idx,
                    status=WorkoutStatus.pending
                )
                self.db.add(exercise)
                total_exercises += 1

            created_days.append({
                "day_id": str(day.id),
                "day_number": day_number,
                "name": day_name,
                "exercises_count": len(exercises)
            })

        await self.db.commit()

        return {
            "success": True,
            "week_id": week_id,
            "week_number": week.week_number,
            "days_created": len(created_days),
            "total_exercises": total_exercises,
            "days": created_days,
            "message": f"Created {len(created_days)} days with {total_exercises} exercises for week {week.week_number}"
        }

    async def _update_exercise(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update an exercise's details"""
        exercise_id = args.get("exercise_id")
        name = args.get("name")
        sets = args.get("sets")
        reps = args.get("reps")
        weight = args.get("weight")
        rest_seconds = args.get("rest_seconds")
        comments = args.get("comments")

        if not exercise_id:
            return {"error": "exercise_id is required"}

        try:
            exercise_uuid = UUID(exercise_id) if isinstance(exercise_id, str) else exercise_id
        except (ValueError, TypeError):
            return {"error": f"Invalid exercise_id format: {exercise_id}"}

        query = select(DayExercise).where(DayExercise.id == exercise_uuid)
        result = await self.db.execute(query)
        exercise = result.scalar_one_or_none()

        if not exercise:
            return {"error": f"Exercise {exercise_id} not found"}

        # Update fields if provided
        if name is not None:
            exercise.name = name
        if sets is not None:
            exercise.sets = sets
        if reps is not None:
            exercise.reps = reps
        if weight is not None:
            exercise.weight = weight
        if rest_seconds is not None:
            exercise.rest_seconds = rest_seconds
        if comments is not None:
            exercise.comments = comments

        await self.db.commit()

        return {
            "success": True,
            "message": f"Updated exercise '{exercise.name}'",
            "exercise_id": str(exercise.id)
        }

    async def _bulk_update_exercises(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update multiple exercises in a single transaction."""
        updates = args.get("updates", [])

        if not updates:
            return {"error": "No updates provided"}

        updated_count = 0
        errors = []

        for update in updates:
            exercise_id = update.get("exercise_id")
            if not exercise_id:
                errors.append("Missing exercise_id in update")
                continue

            try:
                exercise_uuid = UUID(exercise_id) if isinstance(exercise_id, str) else exercise_id
            except (ValueError, TypeError):
                errors.append(f"Invalid exercise_id format: {exercise_id}")
                continue

            try:
                query = select(DayExercise).where(DayExercise.id == exercise_uuid)
                result = await self.db.execute(query)
                exercise = result.scalar_one_or_none()

                if not exercise:
                    errors.append(f"Exercise {exercise_id} not found")
                    continue

                # Update fields if provided
                if update.get("name") is not None:
                    exercise.name = update["name"]
                if update.get("sets") is not None:
                    exercise.sets = update["sets"]
                if update.get("reps") is not None:
                    exercise.reps = update["reps"]
                if update.get("weight") is not None:
                    exercise.weight = update["weight"]
                if update.get("rest_seconds") is not None:
                    exercise.rest_seconds = update["rest_seconds"]
                if update.get("comments") is not None:
                    exercise.comments = update["comments"]

                updated_count += 1

            except Exception as e:
                errors.append(f"Error updating {exercise_id}: {str(e)}")

        await self.db.commit()

        return {
            "success": updated_count > 0,
            "updated_count": updated_count,
            "total_requested": len(updates),
            "errors": errors if errors else None,
            "message": f"Updated {updated_count} exercises" + (f" ({len(errors)} errors)" if errors else "")
        }

    async def _delete_exercise(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete an exercise from a training day"""
        exercise_id = args.get("exercise_id")

        if not exercise_id:
            return {"error": "exercise_id is required"}

        try:
            exercise_uuid = UUID(exercise_id) if isinstance(exercise_id, str) else exercise_id
        except (ValueError, TypeError):
            return {"error": f"Invalid exercise_id format: {exercise_id}"}

        query = select(DayExercise).where(DayExercise.id == exercise_uuid)
        result = await self.db.execute(query)
        exercise = result.scalar_one_or_none()

        if not exercise:
            return {"error": f"Exercise {exercise_id} not found"}

        exercise_name = exercise.name
        await self.db.delete(exercise)
        await self.db.commit()

        return {
            "success": True,
            "message": f"Deleted exercise '{exercise_name}'"
        }

    async def _mark_day_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Change the status of a training day"""
        day_id = args.get("day_id")
        status = args.get("status")

        if not day_id:
            return {"error": "day_id is required"}

        try:
            day_uuid = UUID(day_id) if isinstance(day_id, str) else day_id
        except (ValueError, TypeError):
            return {"error": f"Invalid day_id format: {day_id}"}

        # Validate status
        try:
            new_status = WorkoutStatus(status)
        except ValueError:
            return {"error": f"Invalid status '{status}'. Must be one of: pending, in_progress, completed, skipped"}

        query = select(PlanDay).where(PlanDay.id == day_uuid)
        result = await self.db.execute(query)
        day = result.scalar_one_or_none()

        if not day:
            return {"error": f"Training day {day_id} not found"}

        old_status = day.status.value
        day.status = new_status
        await self.db.commit()

        return {
            "success": True,
            "message": f"Changed '{day.name}' status from '{old_status}' to '{status}'",
            "day_id": str(day.id),
            "day_name": day.name
        }

    async def _delete_day_from_week(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a specific training day from a week"""
        day_id = args.get("day_id")

        if not day_id:
            return {"error": "day_id is required"}

        try:
            day_uuid = UUID(day_id) if isinstance(day_id, str) else day_id
        except (ValueError, TypeError):
            return {"error": f"Invalid day_id format: {day_id}"}

        # Get the day with its week and plan to verify ownership
        query = (
            select(PlanDay)
            .where(PlanDay.id == day_uuid)
            .options(
                selectinload(PlanDay.week).selectinload(PlanWeek.plan)
            )
        )
        result = await self.db.execute(query)
        day = result.scalar_one_or_none()

        if not day:
            return {"error": f"Training day {day_id} not found"}

        # Verify the plan belongs to the current user
        if day.week.plan.user_id != self.user_id:
            return {"error": f"Training day {day_id} does not belong to your plan"}

        day_name = day.name
        week_number = day.week.week_number
        plan_name = day.week.plan.name

        # Delete the day (cascade will delete all exercises)
        await self.db.delete(day)
        await self.db.commit()

        return {
            "success": True,
            "message": f"Deleted day '{day_name}' from week {week_number} of plan '{plan_name}'",
            "deleted_day_name": day_name,
            "week_number": week_number,
            "plan_name": plan_name
        }

    async def _search_workout_memory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search workout history using RAG"""
        from app.providers import get_embedding_provider, get_rag_provider

        query = args.get("query")
        limit = args.get("limit", 5)

        if not query:
            return {"error": "query is required"}

        embedding_provider = get_embedding_provider()
        if not embedding_provider:
            return {"error": "RAG not enabled. Set FITNESS_EMBEDDING_PROVIDER in .env"}

        rag_provider = await get_rag_provider()
        if not rag_provider:
            return {"error": "RAG not enabled. Set FITNESS_RAG_PROVIDER in .env"}

        try:
            # Get query embedding
            query_embedding = await embedding_provider.embed(query)

            # Search with user filter
            results = await rag_provider.search(
                query_embedding,
                limit=limit,
                filter={"user_id": str(self.user_id)}
            )

            return {
                "results": [
                    {
                        "content": r.content,
                        "score": r.score,
                        "metadata": r.metadata
                    }
                    for r in results
                ],
                "count": len(results)
            }
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return {"error": f"Search failed: {str(e)}"}

    async def _store_fitness_insight(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Store fitness insight in RAG"""
        from app.providers import get_embedding_provider, get_rag_provider
        import uuid
        from datetime import datetime

        content = args.get("content")
        category = args.get("category", "note")

        if not content:
            return {"error": "content is required"}

        embedding_provider = get_embedding_provider()
        if not embedding_provider:
            return {"error": "RAG not enabled. Set FITNESS_EMBEDDING_PROVIDER in .env"}

        rag_provider = await get_rag_provider()
        if not rag_provider:
            return {"error": "RAG not enabled. Set FITNESS_RAG_PROVIDER in .env"}

        try:
            # Generate embedding
            embedding = await embedding_provider.embed(content)

            # Store with metadata
            doc_id = str(uuid.uuid4())
            await rag_provider.store(
                id=doc_id,
                content=content,
                embedding=embedding,
                metadata={
                    "user_id": str(self.user_id),
                    "category": category,
                    "created_at": datetime.utcnow().isoformat(),
                    "type": "insight"
                }
            )

            return {
                "success": True,
                "message": f"Stored {category} insight",
                "id": doc_id
            }
        except Exception as e:
            logger.error(f"RAG store failed: {e}")
            return {"error": f"Store failed: {str(e)}"}

    async def _get_exercise_alternatives(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find alternative exercises that work the same muscle groups"""
        from app.providers import get_graph_provider

        exercise_name = args.get("exercise_name")
        if not exercise_name:
            return {"error": "exercise_name is required"}

        graph = await get_graph_provider()
        if not graph:
            return {
                "alternatives": [],
                "message": "Exercise knowledge graph not configured. Enable with FITNESS_GRAPH_PROVIDER=networkx"
            }

        try:
            # Normalize exercise name to ID format
            exercise_id = exercise_name.lower().replace(" ", "_").replace("-", "_")

            # Find direct alternatives
            alternatives = await graph.get_related(
                exercise_id,
                relationship="alternative_to",
                direction="both"
            )

            if not alternatives:
                # If no direct alternatives, find exercises targeting same muscles
                target_muscles = await graph.get_related(
                    exercise_id,
                    relationship="targets",
                    direction="outgoing"
                )

                if target_muscles:
                    # Find other exercises targeting these muscles
                    similar_exercises = []
                    for muscle in target_muscles:
                        exercises = await graph.get_related(
                            muscle.node_id,
                            relationship="targets",
                            direction="incoming"
                        )
                        similar_exercises.extend([ex for ex in exercises if ex.node_id != exercise_id])

                    # Deduplicate
                    seen = set()
                    alternatives = []
                    for ex in similar_exercises:
                        if ex.node_id not in seen:
                            seen.add(ex.node_id)
                            alternatives.append(ex)

            return {
                "exercise": exercise_name,
                "alternatives": [
                    {
                        "id": alt.node_id,
                        "name": alt.properties.get("name", alt.node_id.title()),
                        "reason": alt.properties.get("reason", "Works similar muscle groups")
                    }
                    for alt in alternatives
                ],
                "count": len(alternatives)
            }

        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            return {"error": f"Failed to find alternatives: {str(e)}"}

    async def _get_exercise_progression(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get the progression path for an exercise"""
        from app.providers import get_graph_provider

        exercise_name = args.get("exercise_name")
        if not exercise_name:
            return {"error": "exercise_name is required"}

        graph = await get_graph_provider()
        if not graph:
            return {
                "progression": [],
                "message": "Exercise knowledge graph not configured. Enable with FITNESS_GRAPH_PROVIDER=networkx"
            }

        try:
            # Normalize exercise name
            exercise_id = exercise_name.lower().replace(" ", "_").replace("-", "_")

            # Find easier variations (incoming progresses_to)
            easier = await graph.get_related(
                exercise_id,
                relationship="progresses_to",
                direction="incoming"
            )

            # Find harder variations (outgoing progresses_to)
            harder = await graph.get_related(
                exercise_id,
                relationship="progresses_to",
                direction="outgoing"
            )

            return {
                "exercise": exercise_name,
                "easier_variations": [
                    {
                        "id": ex.node_id,
                        "name": ex.properties.get("name", ex.node_id.title())
                    }
                    for ex in easier
                ],
                "harder_variations": [
                    {
                        "id": ex.node_id,
                        "name": ex.properties.get("name", ex.node_id.title())
                    }
                    for ex in harder
                ],
                "message": f"Found {len(easier)} easier and {len(harder)} harder variations"
            }

        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            return {"error": f"Failed to find progression: {str(e)}"}

    async def _get_muscles_for_exercise(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get which muscle groups an exercise targets"""
        from app.providers import get_graph_provider

        exercise_name = args.get("exercise_name")
        if not exercise_name:
            return {"error": "exercise_name is required"}

        graph = await get_graph_provider()
        if not graph:
            return {
                "muscles": [],
                "message": "Exercise knowledge graph not configured. Enable with FITNESS_GRAPH_PROVIDER=networkx"
            }

        try:
            # Normalize exercise name
            exercise_id = exercise_name.lower().replace(" ", "_").replace("-", "_")

            # Find target muscles
            muscles = await graph.get_related(
                exercise_id,
                relationship="targets",
                direction="outgoing"
            )

            # Separate primary and secondary muscles based on edge properties
            primary_muscles = []
            secondary_muscles = []

            for muscle in muscles:
                # Get edge data to check if primary
                if muscle.node_id in graph.graph.successors(exercise_id):
                    edge_data = graph.graph.get_edge_data(exercise_id, muscle.node_id)
                    if edge_data and edge_data.get("primary"):
                        primary_muscles.append(muscle)
                    else:
                        secondary_muscles.append(muscle)

            return {
                "exercise": exercise_name,
                "primary_muscles": [
                    {
                        "id": m.node_id,
                        "name": m.properties.get("name", m.node_id.title())
                    }
                    for m in primary_muscles
                ],
                "secondary_muscles": [
                    {
                        "id": m.node_id,
                        "name": m.properties.get("name", m.node_id.title())
                    }
                    for m in secondary_muscles
                ],
                "total_muscles": len(muscles)
            }

        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            return {"error": f"Failed to find muscles: {str(e)}"}

    async def _get_exercises_for_muscle(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find exercises that target a specific muscle group"""
        from app.providers import get_graph_provider

        muscle_group = args.get("muscle_group")
        if not muscle_group:
            return {"error": "muscle_group is required"}

        graph = await get_graph_provider()
        if not graph:
            return {
                "exercises": [],
                "message": "Exercise knowledge graph not configured. Enable with FITNESS_GRAPH_PROVIDER=networkx"
            }

        try:
            # Normalize muscle group name
            muscle_id = muscle_group.lower().replace(" ", "_")

            # Find exercises targeting this muscle
            exercises = await graph.get_related(
                muscle_id,
                relationship="targets",
                direction="incoming"
            )

            return {
                "muscle_group": muscle_group,
                "exercises": [
                    {
                        "id": ex.node_id,
                        "name": ex.properties.get("name", ex.node_id.title())
                    }
                    for ex in exercises
                ],
                "count": len(exercises)
            }

        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            return {"error": f"Failed to find exercises: {str(e)}"}
