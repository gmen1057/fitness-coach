"""
RAG Indexer - Automatically indexes fitness data for semantic search.

Called when:
- Workout plan is created
- Workout day is completed
- User stores an insight
"""
import logging
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.fitness import WorkoutPlan, PlanWeek, PlanDay, DayExercise

logger = logging.getLogger(__name__)


async def get_rag_providers():
    """Get embedding and RAG providers if available"""
    from app.providers import get_embedding_provider, get_rag_provider

    embedding = get_embedding_provider()
    if not embedding:
        return None, None

    rag = await get_rag_provider()
    return embedding, rag


async def index_workout_plan(db: AsyncSession, plan_id: UUID, user_id: UUID) -> bool:
    """
    Index a workout plan for RAG search.

    Creates embeddings for:
    - Plan overview (name, goal, description)
    - Each workout day with exercises
    """
    embedding_provider, rag_provider = await get_rag_providers()
    if not embedding_provider or not rag_provider:
        logger.debug("RAG not enabled, skipping indexing")
        return False

    try:
        # Load plan with all data
        query = (
            select(WorkoutPlan)
            .where(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == user_id)
            .options(
                selectinload(WorkoutPlan.weeks)
                .selectinload(PlanWeek.days)
                .selectinload(PlanDay.exercises)
            )
        )
        result = await db.execute(query)
        plan = result.scalar_one_or_none()

        if not plan:
            logger.warning(f"Plan {plan_id} not found for indexing")
            return False

        # Index plan overview
        plan_text = f"Workout plan: {plan.name}. Goal: {plan.goal or 'General fitness'}. {plan.description or ''}"
        plan_embedding = await embedding_provider.embed(plan_text)

        await rag_provider.store(
            id=f"plan-{plan.id}",
            content=plan_text,
            embedding=plan_embedding,
            metadata={
                "user_id": str(user_id),
                "type": "plan",
                "plan_id": str(plan.id),
                "plan_name": plan.name,
                "created_at": datetime.utcnow().isoformat()
            }
        )

        # Index each day
        for week in plan.weeks:
            for day in week.days:
                exercises_text = ", ".join([
                    f"{ex.name} ({ex.sets}x{ex.reps})"
                    for ex in sorted(day.exercises, key=lambda e: e.order_index)
                ])

                day_text = f"Week {week.week_number}, Day {day.day_number}: {day.name or 'Workout'}. Exercises: {exercises_text}"
                day_embedding = await embedding_provider.embed(day_text)

                await rag_provider.store(
                    id=f"day-{day.id}",
                    content=day_text,
                    embedding=day_embedding,
                    metadata={
                        "user_id": str(user_id),
                        "type": "workout_day",
                        "plan_id": str(plan.id),
                        "day_id": str(day.id),
                        "week_number": week.week_number,
                        "day_number": day.day_number,
                        "created_at": datetime.utcnow().isoformat()
                    }
                )

        logger.info(f"Indexed plan {plan.name} with {sum(len(w.days) for w in plan.weeks)} days")
        return True

    except Exception as e:
        logger.error(f"Failed to index plan {plan_id}: {e}")
        return False


async def index_completed_workout(
    db: AsyncSession,
    day_id: UUID,
    user_id: UUID,
    duration_minutes: Optional[int] = None,
    notes: Optional[str] = None
) -> bool:
    """
    Index a completed workout for RAG search.

    Stores the completion event with context.
    """
    embedding_provider, rag_provider = await get_rag_providers()
    if not embedding_provider or not rag_provider:
        return False

    try:
        # Load day with exercises
        query = (
            select(PlanDay)
            .where(PlanDay.id == day_id)
            .options(
                selectinload(PlanDay.exercises),
                selectinload(PlanDay.week).selectinload(PlanWeek.plan)
            )
        )
        result = await db.execute(query)
        day = result.scalar_one_or_none()

        if not day:
            return False

        exercises_text = ", ".join([ex.name for ex in day.exercises])
        completion_text = f"Completed workout: {day.name or 'Training'}. Exercises: {exercises_text}."

        if duration_minutes:
            completion_text += f" Duration: {duration_minutes} minutes."
        if notes:
            completion_text += f" Notes: {notes}"

        embedding = await embedding_provider.embed(completion_text)

        await rag_provider.store(
            id=f"completed-{day.id}-{datetime.utcnow().strftime('%Y%m%d')}",
            content=completion_text,
            embedding=embedding,
            metadata={
                "user_id": str(user_id),
                "type": "completed_workout",
                "day_id": str(day.id),
                "plan_id": str(day.week.plan.id),
                "completed_at": datetime.utcnow().isoformat(),
                "duration_minutes": duration_minutes
            }
        )

        logger.info(f"Indexed completed workout: {day.name}")
        return True

    except Exception as e:
        logger.error(f"Failed to index completed workout {day_id}: {e}")
        return False
