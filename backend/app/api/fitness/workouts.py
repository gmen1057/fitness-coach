"""
Fitness Workouts API.

Endpoints for tracking workout completion and statistics.
"""
from datetime import date, datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.api.deps import get_user_id
from app.models.fitness import (
    WorkoutPlan,
    PlanWeek,
    PlanDay,
    WorkoutStatus,
    WorkoutLog
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class CompleteDayRequest(BaseModel):
    """Request to complete a workout day."""
    day_id: UUID
    notes: Optional[str] = Field(None, max_length=1000, description="Optional workout notes")
    overall_feeling: Optional[str] = Field(None, description="How you felt: easy, normal, hard, exhausted")
    duration_minutes: Optional[int] = Field(None, ge=1, description="Actual workout duration")


class SkipDayRequest(BaseModel):
    """Request to skip a workout day."""
    day_id: UUID
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for skipping")


class DayCompletionResponse(BaseModel):
    """Response after completing/skipping a day."""
    day_id: UUID
    status: str
    completed_at: Optional[datetime] = None
    message: str


class WorkoutStatsResponse(BaseModel):
    """Workout statistics."""
    total_workouts: int
    completed_workouts: int
    skipped_workouts: int
    completion_rate: float
    current_streak: int
    longest_streak: int
    total_duration_minutes: int
    avg_duration_minutes: float
    workouts_this_week: int
    workouts_this_month: int


class WeeklyProgressResponse(BaseModel):
    """Weekly progress breakdown."""
    week_start: date
    week_end: date
    planned: int
    completed: int
    skipped: int


class ProgressHistoryResponse(BaseModel):
    """Progress history with weekly breakdown."""
    weeks: List[WeeklyProgressResponse]
    stats: WorkoutStatsResponse


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/workouts/complete-day", response_model=DayCompletionResponse)
async def complete_workout_day(
    request: CompleteDayRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
):
    """
    Mark a workout day as completed.

    Updates the day status and records completion metadata.

    Args:
        request: Completion request with day_id and optional metadata

    Returns:
        Completion confirmation

    Raises:
        HTTPException: 404 if day not found, 400 if already completed
    """
    # Get the day with plan info to verify ownership
    query = (
        select(PlanDay)
        .join(PlanWeek)
        .join(WorkoutPlan)
        .where(
            PlanDay.id == request.day_id,
            WorkoutPlan.user_id == user_id
        )
    )

    result = await db.execute(query)
    day = result.scalar_one_or_none()

    if not day:
        raise HTTPException(status_code=404, detail="Workout day not found")

    if day.status == WorkoutStatus.completed:
        raise HTTPException(status_code=400, detail="Workout day already completed")

    # Mark as completed
    now = datetime.utcnow()
    day.status = WorkoutStatus.completed
    day.updated_at = now

    # Create workout log entry
    workout_log = WorkoutLog(
        user_id=user_id,
        day_id=day.id,
        started_at=now - timedelta(minutes=request.duration_minutes or 60),
        completed_at=now,
        duration_minutes=request.duration_minutes,
        overall_feeling=request.overall_feeling,
        notes=request.notes,
        synced=True
    )
    db.add(workout_log)

    await db.commit()

    return DayCompletionResponse(
        day_id=day.id,
        status="completed",
        completed_at=now,
        message="Great job! Workout completed successfully."
    )


@router.post("/workouts/skip-day", response_model=DayCompletionResponse)
async def skip_workout_day(
    request: SkipDayRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
):
    """
    Skip a workout day with a reason.

    Records the skip with the provided reason for tracking.

    Args:
        request: Skip request with day_id and reason

    Returns:
        Skip confirmation

    Raises:
        HTTPException: 404 if day not found, 400 if already completed/skipped
    """
    # Get the day with ownership check
    query = (
        select(PlanDay)
        .join(PlanWeek)
        .join(WorkoutPlan)
        .where(
            PlanDay.id == request.day_id,
            WorkoutPlan.user_id == user_id
        )
    )

    result = await db.execute(query)
    day = result.scalar_one_or_none()

    if not day:
        raise HTTPException(status_code=404, detail="Workout day not found")

    if day.status in (WorkoutStatus.completed, WorkoutStatus.skipped):
        raise HTTPException(status_code=400, detail="Cannot skip an already completed or skipped workout")

    # Mark as skipped
    now = datetime.utcnow()
    day.status = WorkoutStatus.skipped
    day.notes = f"Skipped: {request.reason}" if not day.notes else f"{day.notes}\nSkipped: {request.reason}"
    day.updated_at = now

    # Create workout log entry for skip
    workout_log = WorkoutLog(
        user_id=user_id,
        day_id=day.id,
        completed_at=now,
        notes=f"Skipped: {request.reason}",
        synced=True
    )
    db.add(workout_log)

    await db.commit()

    return DayCompletionResponse(
        day_id=day.id,
        status="skipped",
        completed_at=now,
        message=f"Workout skipped. Reason: {request.reason}"
    )


@router.get("/workouts/stats", response_model=WorkoutStatsResponse)
async def get_workout_stats(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
    plan_id: Optional[UUID] = Query(None, description="Filter by specific plan"),
):
    """
    Get workout statistics.

    Returns completion rates, streaks, and duration stats.

    Args:
        plan_id: Optional plan filter

    Returns:
        Comprehensive workout statistics
    """
    # Build base filter
    base_filter = [WorkoutPlan.user_id == user_id]
    if plan_id:
        base_filter.append(WorkoutPlan.id == plan_id)

    # Total days
    total_query = (
        select(func.count())
        .select_from(PlanDay)
        .join(PlanWeek)
        .join(WorkoutPlan)
        .where(and_(*base_filter))
    )
    total_result = await db.execute(total_query)
    total_workouts = total_result.scalar() or 0

    # Completed workouts
    completed_query = (
        select(func.count())
        .select_from(PlanDay)
        .join(PlanWeek)
        .join(WorkoutPlan)
        .where(
            and_(*base_filter),
            PlanDay.status == WorkoutStatus.completed
        )
    )
    completed_result = await db.execute(completed_query)
    completed_workouts = completed_result.scalar() or 0

    # Skipped workouts
    skipped_query = (
        select(func.count())
        .select_from(PlanDay)
        .join(PlanWeek)
        .join(WorkoutPlan)
        .where(
            and_(*base_filter),
            PlanDay.status == WorkoutStatus.skipped
        )
    )
    skipped_result = await db.execute(skipped_query)
    skipped_workouts = skipped_result.scalar() or 0

    # Completion rate
    done_count = completed_workouts + skipped_workouts
    completion_rate = (completed_workouts / done_count * 100) if done_count > 0 else 0.0

    # Get workout logs for duration and streak calculations
    logs_query = (
        select(WorkoutLog)
        .where(
            WorkoutLog.user_id == user_id,
            WorkoutLog.completed_at.isnot(None)
        )
        .order_by(WorkoutLog.completed_at.desc())
    )
    logs_result = await db.execute(logs_query)
    logs = logs_result.scalars().all()

    # For duration stats, filter logs with duration
    completed_logs_with_duration = [log for log in logs if log.duration_minutes]

    # Calculate duration stats (only logs with duration)
    durations = [log.duration_minutes for log in completed_logs_with_duration if log.duration_minutes]
    total_duration = sum(durations)
    avg_duration = (total_duration / len(durations)) if durations else 0.0

    # Calculate streaks based on ALL completed workouts (with or without duration)
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    prev_date = None

    for log in logs:
        if not log.completed_at:
            continue
        log_date = log.completed_at.date()
        if prev_date is None:
            temp_streak = 1
            # Check if current streak is still active (within last 2 days)
            if (date.today() - log_date).days <= 1:
                current_streak = 1
        elif (prev_date - log_date).days == 1:
            temp_streak += 1
            if current_streak > 0:
                current_streak = temp_streak
        else:
            if temp_streak > longest_streak:
                longest_streak = temp_streak
            temp_streak = 1
            if current_streak > 0 and (prev_date - log_date).days > 1:
                current_streak = 0

        prev_date = log_date

    if temp_streak > longest_streak:
        longest_streak = temp_streak

    # Workouts this week (count all completed, with or without duration)
    week_start = date.today() - timedelta(days=date.today().weekday())
    week_query = (
        select(func.count())
        .select_from(PlanDay)
        .join(PlanWeek)
        .join(WorkoutPlan)
        .where(
            WorkoutPlan.user_id == user_id,
            PlanDay.status == WorkoutStatus.completed,
            func.date(PlanDay.updated_at) >= week_start
        )
    )
    week_result = await db.execute(week_query)
    workouts_this_week = week_result.scalar() or 0

    # Workouts this month (count all completed, with or without duration)
    month_start = date.today().replace(day=1)
    month_query = (
        select(func.count())
        .select_from(PlanDay)
        .join(PlanWeek)
        .join(WorkoutPlan)
        .where(
            WorkoutPlan.user_id == user_id,
            PlanDay.status == WorkoutStatus.completed,
            func.date(PlanDay.updated_at) >= month_start
        )
    )
    month_result = await db.execute(month_query)
    workouts_this_month = month_result.scalar() or 0

    return WorkoutStatsResponse(
        total_workouts=total_workouts,
        completed_workouts=completed_workouts,
        skipped_workouts=skipped_workouts,
        completion_rate=round(completion_rate, 1),
        current_streak=current_streak,
        longest_streak=longest_streak,
        total_duration_minutes=total_duration,
        avg_duration_minutes=round(avg_duration, 1),
        workouts_this_week=workouts_this_week,
        workouts_this_month=workouts_this_month
    )
