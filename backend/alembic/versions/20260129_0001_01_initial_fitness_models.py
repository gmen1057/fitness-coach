"""Initial fitness models

Revision ID: 01
Revises:
Create Date: 2026-01-29

Creates all initial tables for the Fitness Coach application:
- workout_plans: Top-level workout plans
- plan_weeks: Weekly breakdown of plans
- plan_days: Daily workouts within weeks
- day_warmups: Warmup instructions for days
- day_exercises: Individual exercises for days
- workout_logs: Completed workout sessions
- exercise_results: Performance tracking for exercises
- chat_messages: AI conversation history
- user_sessions: Claude Agent SDK session storage
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '01'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create workout_status enum
    workout_status = postgresql.ENUM(
        'pending', 'in_progress', 'completed', 'skipped',
        name='workout_status',
        create_type=True
    )
    workout_status.create(op.get_bind(), checkfirst=True)

    # Create workout_plans table
    op.create_table(
        'workout_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('goal', sa.String(255), nullable=True),
        sa.Column('total_weeks', sa.Integer, nullable=False, server_default='12'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_workout_plans_user_id', 'workout_plans', ['user_id'])
    op.create_index('ix_workout_plans_user_active', 'workout_plans', ['user_id', 'is_active'])

    # Create plan_weeks table
    op.create_table(
        'plan_weeks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workout_plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('week_number', sa.Integer, nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'in_progress', 'completed', 'skipped', name='workout_status', create_type=False), nullable=False, server_default='pending'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_plan_weeks_plan_id', 'plan_weeks', ['plan_id'])
    op.create_index('ix_plan_weeks_plan_week', 'plan_weeks', ['plan_id', 'week_number'])

    # Create plan_days table
    op.create_table(
        'plan_days',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('week_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plan_weeks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('day_number', sa.Integer, nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'in_progress', 'completed', 'skipped', name='workout_status', create_type=False), nullable=False, server_default='pending'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_plan_days_week_id', 'plan_days', ['week_id'])
    op.create_index('ix_plan_days_week_day', 'plan_days', ['week_id', 'day_number'])

    # Create day_warmups table
    op.create_table(
        'day_warmups',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('day_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plan_days.id', ondelete='CASCADE'), nullable=False),
        sa.Column('instructions', sa.Text, nullable=False),
        sa.Column('comments', sa.Text, nullable=True),
        sa.Column('duration_minutes', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_day_warmups_day_id', 'day_warmups', ['day_id'])

    # Create day_exercises table
    op.create_table(
        'day_exercises',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('day_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plan_days.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('sets', sa.Integer, nullable=False, server_default='3'),
        sa.Column('reps', sa.String(50), nullable=True),
        sa.Column('weight', sa.String(50), nullable=True),
        sa.Column('rest_seconds', sa.Integer, nullable=True, server_default='120'),
        sa.Column('status', postgresql.ENUM('pending', 'in_progress', 'completed', 'skipped', name='workout_status', create_type=False), nullable=False, server_default='pending'),
        sa.Column('comments', sa.Text, nullable=True),
        sa.Column('order_index', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_day_exercises_day_id', 'day_exercises', ['day_id'])
    op.create_index('ix_day_exercises_day_order', 'day_exercises', ['day_id', 'order_index'])

    # Create workout_logs table
    op.create_table(
        'workout_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('day_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plan_days.id', ondelete='SET NULL'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_minutes', sa.Integer, nullable=True),
        sa.Column('overall_feeling', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('synced', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_workout_logs_user_id', 'workout_logs', ['user_id'])
    op.create_index('ix_workout_logs_user_date', 'workout_logs', ['user_id', 'completed_at'])
    op.create_index('ix_workout_logs_day', 'workout_logs', ['day_id'])

    # Create exercise_results table
    op.create_table(
        'exercise_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workout_log_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workout_logs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('exercise_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('day_exercises.id', ondelete='SET NULL'), nullable=True),
        sa.Column('planned_sets', sa.Integer, nullable=True),
        sa.Column('planned_reps', sa.String(50), nullable=True),
        sa.Column('planned_weight', sa.String(50), nullable=True),
        sa.Column('actual_sets', sa.Integer, nullable=True),
        sa.Column('actual_reps', sa.String(50), nullable=True),
        sa.Column('actual_weight', sa.String(50), nullable=True),
        sa.Column('feeling', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_exercise_results_log', 'exercise_results', ['workout_log_id'])
    op.create_index('ix_exercise_results_exercise', 'exercise_results', ['exercise_id'])

    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('tool_calls', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_chat_messages_user_id', 'chat_messages', ['user_id'])

    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('module', sa.String(50), nullable=False, server_default='fitness'),
        sa.Column('session_id', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_unique_constraint('uq_user_session_module', 'user_sessions', ['user_id', 'module'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('user_sessions')
    op.drop_table('chat_messages')
    op.drop_table('exercise_results')
    op.drop_table('workout_logs')
    op.drop_table('day_exercises')
    op.drop_table('day_warmups')
    op.drop_table('plan_days')
    op.drop_table('plan_weeks')
    op.drop_table('workout_plans')

    # Drop enum
    workout_status = postgresql.ENUM('pending', 'in_progress', 'completed', 'skipped', name='workout_status')
    workout_status.drop(op.get_bind(), checkfirst=True)
