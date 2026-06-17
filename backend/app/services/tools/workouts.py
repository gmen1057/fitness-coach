"""Workout execution, scheduling, stats, history, result logging and RAG workout memory tools."""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.fitness import (
    BloodMarker,
    BodyWeightLog,
    DayExercise,
    ExerciseResult,
    InjuryEpisode,
    PlanDay,
    PlanWeek,
    WorkoutLog,
    WorkoutPlan,
    WorkoutStatus,
)

logger = logging.getLogger(__name__)


WORKOUT_TOOLS = [
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
        "name": "get_workout_history",
        "description": "Get the user's full training history across ALL plans. Returns completed workouts newest-first.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max number of past workouts to return (default 20)",
                    "default": 20
                }
            }
        }
    },
    {
        "name": "get_user_exercise_progression",
        "description": "Get how a specific exercise progressed over time for the user (planned weight vs actual weight). Matches case-insensitively and partially.",
        "parameters": {
            "type": "object",
            "properties": {
                "exercise_name": {
                    "type": "string",
                    "description": "Full or partial exercise name to track"
                }
            },
            "required": ["exercise_name"]
        }
    },
    {
        "name": "log_exercise_results",
        "description": "Record actual per-exercise performance (sets, reps, weight) for a completed workout.",
        "parameters": {
            "type": "object",
            "properties": {
                "day_id": {
                    "type": "string",
                    "description": "UUID of the plan day the results belong to"
                },
                "results": {
                    "type": "array",
                    "description": "List of result objects per exercise",
                    "items": {
                        "type": "object",
                        "properties": {
                            "exercise_id": {
                                "type": "string",
                                "description": "UUID of the exercise (optional if name is given)"
                            },
                            "exercise_name": {
                                "type": "string",
                                "description": "Name of the exercise (optional if ID is given)"
                            },
                            "actual_sets": {
                                "type": "integer",
                                "description": "Actual number of sets completed"
                            },
                            "actual_reps": {
                                "type": "string",
                                "description": "Actual reps completed (e.g. '8')"
                            },
                            "actual_weight": {
                                "type": "string",
                                "description": "Actual weight used (e.g. '50 кг')"
                            },
                            "feeling": {
                                "type": "string",
                                "description": "Subjective feeling: 'easy', 'ok', 'hard', 'failed'"
                            },
                            "notes": {
                                "type": "string",
                                "description": "Optional exercise comments"
                            }
                        }
                    }
                }
            },
            "required": ["day_id", "results"]
        }
    },
]


class WorkoutToolsMixin:
    """Workout execution, scheduling, stats, history, result logging and RAG workout memory tools."""

    async def _get_current_workout(self, args: dict[str, Any]) -> dict[str, Any]:
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

    async def _get_workout_stats(self, args: dict[str, Any]) -> dict[str, Any]:
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

    async def _complete_workout_day(self, args: dict[str, Any]) -> dict[str, Any]:
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

    async def _skip_workout_day(self, args: dict[str, Any]) -> dict[str, Any]:
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

    async def _add_exercise_note(self, args: dict[str, Any]) -> dict[str, Any]:
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

    async def _mark_day_status(self, args: dict[str, Any]) -> dict[str, Any]:
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

    async def _search_workout_memory(self, args: dict[str, Any]) -> dict[str, Any]:
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

    async def _store_fitness_insight(self, args: dict[str, Any]) -> dict[str, Any]:
        """Store fitness insight in RAG"""
        import uuid
        from datetime import datetime

        from app.providers import get_embedding_provider, get_rag_provider

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

    async def _get_workout_history(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get the user's full training history across ALL plans"""
        limit = args.get("limit", 20)
        if limit <= 0 or limit > 200:
            limit = 20

        try:
            # Get total count
            total_query = select(func.count(WorkoutLog.id)).where(WorkoutLog.user_id == self.user_id)
            total_result = await self.db.execute(total_query)
            total = total_result.scalar() or 0

            # Get logs with plan/day names
            query = (
                select(WorkoutLog)
                .where(WorkoutLog.user_id == self.user_id)
                .options(
                    selectinload(WorkoutLog.day)
                    .selectinload(PlanDay.week)
                    .selectinload(PlanWeek.plan)
                )
                .order_by(WorkoutLog.completed_at.desc())
                .limit(limit)
            )

            result = await self.db.execute(query)
            logs = result.scalars().all()

            workouts = []
            for log in logs:
                plan_name = log.day.week.plan.name if log.day and log.day.week and log.day.week.plan else "Unknown Plan"
                day_name = log.day.name if log.day else "Unknown Day"
                week_num = log.day.week.week_number if log.day and log.day.week else 0
                workouts.append({
                    "completed_at": log.completed_at.isoformat(),
                    "duration_minutes": log.duration_minutes,
                    "overall_feeling": log.overall_feeling,
                    "notes": log.notes,
                    "day_name": day_name,
                    "week_number": week_num,
                    "plan_name": plan_name,
                })

            return {
                "total_completed_workouts": total,
                "returned": len(workouts),
                "workouts": workouts,
            }
        except Exception as e:
            logger.error(f"get_workout_history failed: {e}")
            return {"error": str(e)}

    async def _get_user_exercise_progression(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get user's recorded weights and performance progression for a specific exercise"""
        exercise_name = args.get("exercise_name")
        if not exercise_name or not exercise_name.strip():
            return {"error": "exercise_name is required"}

        try:
            # Query exercise results matching name case-insensitively
            query = (
                select(ExerciseResult)
                .join(DayExercise, DayExercise.id == ExerciseResult.exercise_id)
                .join(WorkoutLog, WorkoutLog.id == ExerciseResult.workout_log_id)
                .where(WorkoutLog.user_id == self.user_id)
                .where(func.lower(DayExercise.name).like(f"%{exercise_name.strip().lower()}%"))
                .order_by(WorkoutLog.completed_at.asc())
            )

            result = await self.db.execute(query)
            results = result.scalars().all()

            progression = []
            for r in results:
                progression.append({
                    "exercise_name": exercise_name,
                    "completed_at": r.workout_log.completed_at.isoformat() if r.workout_log else None,
                    "planned_sets": r.planned_sets,
                    "planned_reps": r.planned_reps,
                    "planned_weight": r.planned_weight,
                    "actual_sets": r.actual_sets,
                    "actual_reps": r.actual_reps,
                    "actual_weight": r.actual_weight,
                    "feeling": r.feeling,
                    "notes": r.notes,
                })

            return {
                "exercise_query": exercise_name,
                "data_points": len(progression),
                "progression": progression,
            }
        except Exception as e:
            logger.error(f"get_user_exercise_progression failed: {e}")
            return {"error": str(e)}

    async def _log_exercise_results(self, args: dict[str, Any]) -> dict[str, Any]:
        """Record actual performance for exercises in a day's workout"""
        day_id_str = args.get("day_id")
        results = args.get("results")

        if not day_id_str or not results:
            return {"error": "day_id and results list are required"}

        try:
            day_uuid = UUID(day_id_str)
        except ValueError:
            return {"error": "Invalid day_id format"}

        try:
            # Get latest workout log for this day
            log_query = (
                select(WorkoutLog)
                .where(WorkoutLog.day_id == day_uuid)
                .where(WorkoutLog.user_id == self.user_id)
                .order_by(WorkoutLog.completed_at.desc())
                .limit(1)
            )
            log_res = await self.db.execute(log_query)
            log = log_res.scalar()
            if not log:
                return {"error": "No workout log for this day yet — call complete_workout_day first."}

            saved = []
            errors = []
            for idx, r in enumerate(results):
                ex_id_str = r.get("exercise_id")
                ex_name = r.get("exercise_name")

                ex_id = None
                if ex_id_str:
                    try:
                        ex_id = UUID(ex_id_str)
                    except ValueError:
                        errors.append({"index": idx, "error": "Invalid exercise_id format"})
                        continue
                elif ex_name:
                    # Lookup exercise by name on this day
                    ex_query = (
                        select(DayExercise)
                        .where(DayExercise.day_id == day_uuid)
                        .where(func.lower(DayExercise.name).like(f"%{ex_name.strip().lower()}%"))
                        .limit(1)
                    )
                    ex_res = await self.db.execute(ex_query)
                    found_ex = ex_res.scalar()
                    if found_ex:
                        ex_id = found_ex.id
                    else:
                        errors.append({"index": idx, "error": f"Exercise '{ex_name}' not found on this day"})
                        continue
                else:
                    errors.append({"index": idx, "error": "Either exercise_id or exercise_name must be provided"})
                    continue

                # Fetch original planned stats
                planned_query = select(DayExercise).where(DayExercise.id == ex_id)
                planned_res = await self.db.execute(planned_query)
                p = planned_res.scalar()
                planned_sets = p.sets if p else None
                planned_reps = p.reps if p else None
                planned_weight = p.weight if p else None

                # Create result entry
                res_entry = ExerciseResult(
                    id=uuid.uuid4(),
                    workout_log_id=log.id,
                    exercise_id=ex_id,
                    planned_sets=planned_sets,
                    planned_reps=planned_reps,
                    planned_weight=planned_weight,
                    actual_sets=r.get("actual_sets"),
                    actual_reps=r.get("actual_reps"),
                    actual_weight=r.get("actual_weight"),
                    feeling=r.get("feeling"),
                    notes=r.get("notes"),
                )
                self.db.add(res_entry)
                saved.append({"exercise_id": str(ex_id), "actual_weight": r.get("actual_weight")})

            await self.db.commit()

            payload = {"saved_count": len(saved), "saved": saved}
            if errors:
                payload["errors"] = errors
            return payload
        except Exception as e:
            await self.db.rollback()
            logger.error(f"log_exercise_results failed: {e}")
            return {"error": str(e)}
