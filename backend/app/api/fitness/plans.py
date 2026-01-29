"""
Fitness Plans API.

Endpoints for managing workout plans with weeks, days, and exercises.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.api.deps import get_user_id
from app.models.fitness import (
    WorkoutPlan,
    PlanWeek,
    PlanDay,
    DayWarmup,
    DayExercise,
    WorkoutStatus
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ExerciseResponse(BaseModel):
    """Single exercise in a workout."""
    id: UUID
    name: str
    sets: int
    reps: Optional[str] = None  # Can be "8-10" or "12"
    weight: Optional[str] = None  # Can be "100kg" or "bodyweight"
    rest_seconds: Optional[int] = None
    comments: Optional[str] = None
    order_index: int
    status: str = "pending"

    class Config:
        from_attributes = True


class WarmupResponse(BaseModel):
    """Warmup instructions for a day."""
    id: UUID
    instructions: str
    comments: Optional[str] = None
    duration_minutes: Optional[int] = None

    class Config:
        from_attributes = True


class WorkoutDayResponse(BaseModel):
    """Single workout day."""
    id: UUID
    day_number: int
    name: Optional[str] = None
    notes: Optional[str] = None
    warmups: List[WarmupResponse] = []
    exercises: List[ExerciseResponse] = []
    status: str = "pending"

    class Config:
        from_attributes = True


class WorkoutWeekResponse(BaseModel):
    """Single workout week."""
    id: UUID
    week_number: int
    notes: Optional[str] = None
    status: str = "pending"
    days: List[WorkoutDayResponse] = []

    class Config:
        from_attributes = True


class PlanSummaryResponse(BaseModel):
    """Plan summary for list view."""
    id: UUID
    name: str
    description: Optional[str] = None
    goal: Optional[str] = None
    total_weeks: int
    is_active: bool = False
    created_at: datetime
    progress_percent: float = 0.0
    completed_days: int = 0
    total_days: int = 0

    class Config:
        from_attributes = True


class PlanDetailResponse(BaseModel):
    """Full plan with weeks and days."""
    id: UUID
    name: str
    description: Optional[str] = None
    goal: Optional[str] = None
    total_weeks: int
    is_active: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    weeks: List[WorkoutWeekResponse] = []

    class Config:
        from_attributes = True


class CurrentWorkoutResponse(BaseModel):
    """Current workout day to perform."""
    plan_id: UUID
    plan_name: str
    week_number: int
    day: WorkoutDayResponse
    total_days: int
    completed_days: int
    message: Optional[str] = None


class PlansListResponse(BaseModel):
    """Response for plans list."""
    plans: List[PlanSummaryResponse]
    total: int


class CreatePlanRequest(BaseModel):
    """Request to create a workout plan via AI."""
    description: str = Field(..., min_length=10, max_length=1000)
    goal: Optional[str] = None
    weeks: int = Field(4, ge=1, le=52, description="Number of weeks")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/plans", response_model=PlansListResponse)
async def list_plans(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List all workout plans for the user.

    Returns plans with summary info and progress percentage.

    Args:
        is_active: Filter by active status (None = all plans)
        limit: Maximum number of plans to return
        offset: Number of plans to skip

    Returns:
        List of plans with progress info
    """
    # Build query
    query = select(WorkoutPlan).where(WorkoutPlan.user_id == user_id)

    if is_active is not None:
        query = query.where(WorkoutPlan.is_active == is_active)

    query = query.order_by(WorkoutPlan.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset(offset).limit(limit)

    # Execute
    result = await db.execute(query)
    plans = result.scalars().all()

    # Calculate progress for each plan
    plan_summaries = []
    for plan in plans:
        # Count completed days across all weeks
        days_query = (
            select(
                func.count().filter(PlanDay.status == WorkoutStatus.completed).label('completed'),
                func.count().label('total')
            )
            .select_from(PlanDay)
            .join(PlanWeek)
            .where(PlanWeek.plan_id == plan.id)
        )
        days_result = await db.execute(days_query)
        row = days_result.one()
        completed = row.completed or 0
        total_days = row.total or 0

        progress = (completed / total_days * 100) if total_days > 0 else 0.0

        plan_summaries.append(PlanSummaryResponse(
            id=plan.id,
            name=plan.name,
            description=plan.description,
            goal=plan.goal,
            total_weeks=plan.total_weeks,
            is_active=plan.is_active,
            created_at=plan.created_at,
            progress_percent=round(progress, 1),
            completed_days=completed,
            total_days=total_days
        ))

    return PlansListResponse(plans=plan_summaries, total=total)


@router.get("/plans/{plan_id}", response_model=PlanDetailResponse)
async def get_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
):
    """
    Get a workout plan with all weeks, days, and exercises.

    Returns the complete plan structure for detailed view.

    Args:
        plan_id: Plan UUID

    Returns:
        Full plan with all nested data

    Raises:
        HTTPException: 404 if plan not found
    """
    # Load plan with all relationships
    query = (
        select(WorkoutPlan)
        .where(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == user_id)
        .options(
            selectinload(WorkoutPlan.weeks)
            .selectinload(PlanWeek.days)
            .selectinload(PlanDay.warmups)
        )
        .options(
            selectinload(WorkoutPlan.weeks)
            .selectinload(PlanWeek.days)
            .selectinload(PlanDay.exercises)
        )
    )

    result = await db.execute(query)
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Build response with sorted weeks and days
    weeks_response = []
    for week in sorted(plan.weeks, key=lambda w: w.week_number):
        days_response = []
        for day in sorted(week.days, key=lambda d: d.day_number):
            # Build warmups
            warmups_response = [
                WarmupResponse(
                    id=warmup.id,
                    instructions=warmup.instructions,
                    comments=warmup.comments,
                    duration_minutes=warmup.duration_minutes
                )
                for warmup in day.warmups
            ]

            # Build exercises
            exercises_response = [
                ExerciseResponse(
                    id=ex.id,
                    name=ex.name,
                    sets=ex.sets,
                    reps=ex.reps,
                    weight=ex.weight,
                    rest_seconds=ex.rest_seconds,
                    comments=ex.comments,
                    order_index=ex.order_index,
                    status=ex.status.value if ex.status else "pending"
                )
                for ex in sorted(day.exercises, key=lambda e: e.order_index)
            ]

            days_response.append(WorkoutDayResponse(
                id=day.id,
                day_number=day.day_number,
                name=day.name,
                notes=day.notes,
                warmups=warmups_response,
                exercises=exercises_response,
                status=day.status.value if day.status else "pending"
            ))

        weeks_response.append(WorkoutWeekResponse(
            id=week.id,
            week_number=week.week_number,
            notes=week.notes,
            status=week.status.value if week.status else "pending",
            days=days_response
        ))

    return PlanDetailResponse(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        goal=plan.goal,
        total_weeks=plan.total_weeks,
        is_active=plan.is_active,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        weeks=weeks_response
    )


@router.get("/plans/{plan_id}/current", response_model=CurrentWorkoutResponse)
async def get_current_workout(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
):
    """
    Get the current workout day to perform.

    Returns the next incomplete workout day in the plan.
    If all days are completed, returns the last day with a completion message.

    Args:
        plan_id: Plan UUID

    Returns:
        Current workout to perform

    Raises:
        HTTPException: 404 if plan not found or has no days
    """
    # Load plan with relationships
    query = (
        select(WorkoutPlan)
        .where(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == user_id)
        .options(
            selectinload(WorkoutPlan.weeks)
            .selectinload(PlanWeek.days)
            .selectinload(PlanDay.warmups)
        )
        .options(
            selectinload(WorkoutPlan.weeks)
            .selectinload(PlanWeek.days)
            .selectinload(PlanDay.exercises)
        )
    )

    result = await db.execute(query)
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Flatten all days and sort
    all_days = []
    for week in plan.weeks:
        for day in week.days:
            all_days.append((week.week_number, day))

    all_days.sort(key=lambda x: (x[0], x[1].day_number))

    if not all_days:
        raise HTTPException(status_code=404, detail="Plan has no workout days")

    # Count stats
    total_days = len(all_days)
    completed_days = len([
        d for _, d in all_days
        if d.status in (WorkoutStatus.completed, WorkoutStatus.skipped)
    ])

    # Find first incomplete day (pending or in_progress)
    current_day = None
    current_week = 1

    for week_num, day in all_days:
        if day.status in (WorkoutStatus.pending, WorkoutStatus.in_progress):
            current_day = day
            current_week = week_num
            break

    # If all completed, return last day with message
    message = None
    if current_day is None:
        _, current_day = all_days[-1]
        current_week = all_days[-1][0]
        message = "Congratulations! You have completed all workouts in this plan!"

    # Build warmups
    warmups_response = [
        WarmupResponse(
            id=warmup.id,
            instructions=warmup.instructions,
            comments=warmup.comments,
            duration_minutes=warmup.duration_minutes
        )
        for warmup in current_day.warmups
    ]

    # Build exercise list
    exercises_response = [
        ExerciseResponse(
            id=ex.id,
            name=ex.name,
            sets=ex.sets,
            reps=ex.reps,
            weight=ex.weight,
            rest_seconds=ex.rest_seconds,
            comments=ex.comments,
            order_index=ex.order_index,
            status=ex.status.value if ex.status else "pending"
        )
        for ex in sorted(current_day.exercises, key=lambda e: e.order_index)
    ]

    return CurrentWorkoutResponse(
        plan_id=plan.id,
        plan_name=plan.name,
        week_number=current_week,
        day=WorkoutDayResponse(
            id=current_day.id,
            day_number=current_day.day_number,
            name=current_day.name,
            notes=current_day.notes,
            warmups=warmups_response,
            exercises=exercises_response,
            status=current_day.status.value if current_day.status else "pending"
        ),
        total_days=total_days,
        completed_days=completed_days,
        message=message
    )


@router.post("/plans")
async def create_plan(
    request: CreatePlanRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
):
    """
    Create an empty workout plan structure.

    Creates a plan with the specified number of weeks. The plan can then be
    populated with exercises via the chat interface using AI assistance,
    or through the edit endpoints.

    Args:
        request: Plan creation request with description and goals

    Returns:
        Created plan ID and status message
    """
    import uuid
    from datetime import datetime

    # Create plan
    plan = WorkoutPlan(
        id=uuid.uuid4(),
        user_id=user_id,
        name=request.description[:100],  # Use description as name (truncated)
        description=request.description,
        goal=request.goal,
        total_weeks=request.weeks,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(plan)

    # Create week structures
    for week_num in range(1, request.weeks + 1):
        week = PlanWeek(
            id=uuid.uuid4(),
            plan_id=plan.id,
            week_number=week_num,
            status=WorkoutStatus.pending,
        )
        db.add(week)

    await db.commit()
    await db.refresh(plan)

    return {
        "message": "Workout plan created successfully",
        "plan_id": str(plan.id),
        "plan_name": plan.name
    }
