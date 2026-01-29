# SQLAlchemy Models

Database models for the Fitness Coach application using SQLAlchemy 2.0 with async support.

## Structure

```
app/models/
├── __init__.py              # Base declaration and engine factory
└── fitness/
    ├── __init__.py          # Exports all fitness models
    ├── workout_plan.py      # Workout plan schema
    ├── workout_log.py       # Completed workout tracking
    └── chat_message.py      # Chat history and sessions
```

## Models Overview

### Workout Planning

**WorkoutPlan** - Top-level workout program
- Fields: `name`, `description`, `goal`, `total_weeks`, `is_active`
- Relationships: `weeks` (one-to-many)

**PlanWeek** - Weekly breakdown
- Fields: `week_number`, `status`, `notes`
- Relationships: `plan` (many-to-one), `days` (one-to-many)

**PlanDay** - Daily workout
- Fields: `day_number`, `name`, `status`, `notes`
- Relationships: `week` (many-to-one), `warmups`, `exercises` (one-to-many)

**DayWarmup** - Warmup instructions
- Fields: `instructions`, `comments`, `duration_minutes`

**DayExercise** - Individual exercise
- Fields: `name`, `sets`, `reps`, `weight`, `rest_seconds`, `status`, `comments`, `order_index`

### Workout Logging

**WorkoutLog** - Completed workout session
- Fields: `started_at`, `completed_at`, `duration_minutes`, `overall_feeling`, `notes`, `synced`
- Relationships: `day` (many-to-one), `exercise_results` (one-to-many)

**ExerciseResult** - Actual exercise performance
- Fields: Planned values (`planned_sets`, `planned_reps`, `planned_weight`)
- Fields: Actual values (`actual_sets`, `actual_reps`, `actual_weight`)
- Fields: Feedback (`feeling`, `notes`)

### Chat & Sessions

**ChatMessage** - AI conversation history
- Fields: `role` (user/assistant), `content`, `tool_calls`

**UserSession** - Claude Agent SDK session persistence
- Fields: `module`, `session_id`
- Unique constraint: One session per user per module

## Enums

All enums use **lowercase** values to match PostgreSQL enum serialization.

```python
class WorkoutStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"

class FeelingLevel(str, enum.Enum):
    easy = "easy"
    normal = "normal"
    hard = "hard"
    exhausted = "exhausted"
```

## Usage

### Initialize Database

```python
from app.models import Base, create_engine_and_session, init_db

# Create engine and session factory
engine, async_session = create_engine_and_session(
    database_url="postgresql+asyncpg://user:pass@localhost/fitness",
    echo=False
)

# Create all tables
await init_db(engine)
```

### Query Examples

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.fitness import WorkoutPlan, PlanWeek, PlanDay

# Get plan with all nested data (eager loading)
async with async_session() as db:
    query = (
        select(WorkoutPlan)
        .where(WorkoutPlan.id == plan_id)
        .options(
            selectinload(WorkoutPlan.weeks)
            .selectinload(PlanWeek.days)
            .selectinload(PlanDay.exercises)
        )
    )
    result = await db.execute(query)
    plan = result.scalar_one_or_none()
```

### Create New Plan

```python
from uuid import UUID
from app.models.fitness import WorkoutPlan, PlanWeek, PlanDay, DayExercise

async with async_session() as db:
    plan = WorkoutPlan(
        user_id=UUID("user-uuid-here"),
        name="Strength Training",
        total_weeks=8,
        is_active=True
    )

    week = PlanWeek(week_number=1)
    plan.weeks.append(week)

    day = PlanDay(day_number=1, name="Upper Body")
    week.days.append(day)

    exercise = DayExercise(
        name="Bench Press",
        sets=3,
        reps="8-10",
        weight="80kg",
        rest_seconds=120,
        order_index=1
    )
    day.exercises.append(exercise)

    db.add(plan)
    await db.commit()
    await db.refresh(plan)
```

## Key Design Decisions

1. **User ID required**: All top-level entities require `user_id` (UUID) for multi-user support
2. **Cascade deletes**: Parent deletion cascades to children (plan → weeks → days → exercises)
3. **Status tracking**: Enums for workout status (pending, in_progress, completed, skipped)
4. **Flexible data types**: String fields for `reps` and `weight` support various formats ("8-10", "bodyweight")
5. **Offline support**: `synced` flag in WorkoutLog for PWA offline functionality
6. **Indexes**: Optimized for common queries (user_id, active plans, date ranges)

## Database Connection

Required PostgreSQL connection string format:

```
postgresql+asyncpg://username:password@host:port/database
```

Example:
```
postgresql+asyncpg://fitness_user:secure_pass@localhost:5432/fitness_coach
```

## Migrations

Use Alembic for database migrations:

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```
