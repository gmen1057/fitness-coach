"""
Plan Navigator - compact index for AI agent orientation.

Generates a structured summary of workout plans for fast context injection
into the fitness agent's system prompt. This eliminates the need for
repeated database queries during conversation.

The navigator provides:
- Active plan overview with current progress
- Recent workout history
- Quick stats (streak, completion rate)
- Next workout preview
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.fitness import (
    DayExercise,
    PlanDay,
    PlanWeek,
    WorkoutPlan,
    WorkoutStatus,
)

logger = logging.getLogger(__name__)


class PlanNavigator:
    """
    Generates compact navigation context for the fitness AI agent.

    The navigator creates a structured summary that gives the agent
    instant understanding of:
    - What plans exist and their status
    - Current position in active plan
    - Recent workout history
    - Key statistics

    This context is injected into the system prompt, allowing the agent
    to answer many questions without making tool calls.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(self, user_id: UUID) -> str:
        """
        Generate navigation context for user.

        Args:
            user_id: User identifier

        Returns:
            Formatted navigation string for system prompt
        """
        try:
            nav_data = await self._build_navigation_data(user_id)
            return self._format_navigation(nav_data)
        except Exception as e:
            logger.error(f"Failed to generate navigation: {e}")
            return ""

    async def _build_navigation_data(self, user_id: UUID) -> dict[str, Any]:
        """Build raw navigation data from database."""
        now = datetime.now()
        today = now.date()

        data = {
            "current_datetime": now,
            "today": today,
            "weekday": now.strftime("%A"),
            "active_plan": None,
            "other_plans": [],
            "recent_workouts": [],
            "stats": {},
            "next_workout": None,
            "today_workout": None,
        }

        # Get all user plans with eager loading
        query = (
            select(WorkoutPlan)
            .where(WorkoutPlan.user_id == user_id)
            .options(
                selectinload(WorkoutPlan.weeks)
                .selectinload(PlanWeek.days)
                .selectinload(PlanDay.exercises)
            )
            .order_by(WorkoutPlan.is_active.desc(), WorkoutPlan.updated_at.desc())
        )
        result = await self.db.execute(query)
        plans = result.scalars().all()

        if not plans:
            return data

        # Process each plan
        for plan in plans:
            plan_summary = self._summarize_plan(plan)

            if plan.is_active and data["active_plan"] is None:
                data["active_plan"] = plan_summary
                data["next_workout"] = self._get_next_workout(plan)
                data["recent_workouts"] = self._get_recent_workouts(plan, today=data["today"])
                data["today_workout"] = self._get_today_workout(plan, data["today"])
            else:
                data["other_plans"].append({
                    "name": plan.name,
                    "status": "active" if plan.is_active else "paused",
                    "progress": plan_summary["progress"],
                })

        # Calculate stats from active plan
        if data["active_plan"]:
            data["stats"] = self._calculate_stats(plans[0])

        return data

    def _summarize_plan(self, plan: WorkoutPlan) -> dict[str, Any]:
        """Create compact summary of a plan."""
        total_days = 0
        completed_days = 0
        current_week = None
        current_day = None

        for week in plan.weeks:
            for day in week.days:
                total_days += 1
                if day.status == WorkoutStatus.completed:
                    completed_days += 1
                elif day.status == WorkoutStatus.in_progress:
                    current_week = week.week_number
                    current_day = day
                elif day.status == WorkoutStatus.pending and current_week is None:
                    current_week = week.week_number
                    current_day = day

        progress_percent = round((completed_days / total_days * 100) if total_days > 0 else 0)

        return {
            "id": str(plan.id),
            "name": plan.name,
            "goal": plan.goal,
            "total_weeks": plan.total_weeks,
            "current_week": current_week or 1,
            "current_day": current_day.name if current_day else None,
            "current_day_number": current_day.day_number if current_day else None,
            "progress": f"{progress_percent}%",
            "completed_days": completed_days,
            "total_days": total_days,
        }

    def _get_next_workout(self, plan: WorkoutPlan) -> dict[str, Any] | None:
        """Get next pending workout details."""
        for week in sorted(plan.weeks, key=lambda w: w.week_number):
            for day in sorted(week.days, key=lambda d: d.day_number):
                if day.status in (WorkoutStatus.pending, WorkoutStatus.in_progress):
                    exercises = []
                    for ex in sorted(day.exercises, key=lambda e: e.order_index):
                        exercises.append(f"{ex.name} ({ex.sets}×{ex.reps})")

                    return {
                        "week": week.week_number,
                        "day": day.day_number,
                        "name": day.name,
                        "status": day.status.value,
                        "exercises_count": len(day.exercises),
                        "exercises_preview": exercises[:3],
                    }
        return None

    def _get_today_workout(self, plan: WorkoutPlan, today) -> dict[str, Any] | None:
        """Check if a workout was completed today."""
        for week in plan.weeks:
            for day in week.days:
                if day.status == WorkoutStatus.completed and day.updated_at:
                    day_date = day.updated_at.date() if day.updated_at.tzinfo else day.updated_at.date()
                    if day_date == today:
                        return {
                            "week": week.week_number,
                            "day": day.day_number,
                            "name": day.name,
                        }
        return None

    def _get_recent_workouts(self, plan: WorkoutPlan, limit: int = 5, today=None) -> list[dict[str, Any]]:
        """Get recent completed/skipped workouts."""
        recent = []

        for week in sorted(plan.weeks, key=lambda w: w.week_number, reverse=True):
            for day in sorted(week.days, key=lambda d: d.day_number, reverse=True):
                if day.status in (WorkoutStatus.completed, WorkoutStatus.skipped):
                    is_today = False
                    if today and day.updated_at:
                        day_date = day.updated_at.date() if day.updated_at.tzinfo else day.updated_at.date()
                        is_today = (day_date == today)

                    recent.append({
                        "week": week.week_number,
                        "day": day.day_number,
                        "name": day.name,
                        "status": "✓" if day.status == WorkoutStatus.completed else "⊘",
                        "date": day.updated_at.strftime("%d.%m") if day.updated_at else None,
                        "is_today": is_today,
                    })
                    if len(recent) >= limit:
                        return recent

        return recent

    def _calculate_stats(self, plan: WorkoutPlan) -> dict[str, Any]:
        """Calculate workout statistics."""
        completed = 0
        skipped = 0
        total = 0
        streak = 0
        counting_streak = True

        # Count from most recent
        all_days = []
        for week in plan.weeks:
            for day in week.days:
                all_days.append(day)

        all_days.sort(key=lambda d: (d.week.week_number, d.day_number), reverse=True)

        for day in all_days:
            total += 1
            if day.status == WorkoutStatus.completed:
                completed += 1
                if counting_streak:
                    streak += 1
            elif day.status == WorkoutStatus.skipped:
                skipped += 1
                counting_streak = False
            elif day.status in (WorkoutStatus.pending, WorkoutStatus.in_progress):
                counting_streak = False

        # This week stats
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday())
        this_week_completed = 0
        this_week_total = 0

        for day in all_days:
            day_updated = day.updated_at.replace(tzinfo=None) if day.updated_at and day.updated_at.tzinfo else day.updated_at
            if day_updated and day_updated >= week_start:
                this_week_total += 1
                if day.status == WorkoutStatus.completed:
                    this_week_completed += 1

        return {
            "streak": streak,
            "total_completed": completed,
            "total_skipped": skipped,
            "this_week": f"{this_week_completed}/{this_week_total}" if this_week_total > 0 else "0",
            "completion_rate": f"{round(completed / (completed + skipped) * 100) if (completed + skipped) > 0 else 0}%",
        }

    def _format_navigation(self, data: dict[str, Any]) -> str:
        """Format navigation data as readable context for agent."""
        lines = []

        # Current date/time header
        now = data.get("current_datetime")
        weekday = data.get("weekday", "")
        if now:
            lines.append(f"## Current Time: {now.strftime('%Y-%m-%d %H:%M')} ({weekday})")
            lines.append("")

        if not data.get("active_plan"):
            lines.append("No active workout plans.")
            return "\n".join(lines)

        lines.append("## Workout Plan")

        # Today's workout
        tw = data.get("today_workout")
        if tw:
            lines.append(f"\n✅ **Completed Today:** W{tw['week']}D{tw['day']} — {tw['name'] or 'workout'}")

        # Active plan
        ap = data["active_plan"]
        lines.append(f"\n**Active Plan:** {ap['name']}")
        if ap.get("goal"):
            lines.append(f"Goal: {ap['goal']}")
        lines.append(f"Progress: Week {ap['current_week']}/{ap['total_weeks']}, {ap['progress']} ({ap['completed_days']}/{ap['total_days']} days)")

        # Next workout
        nw = data.get("next_workout")
        if nw and not tw:
            status_label = "🔄 in progress" if nw["status"] == "in_progress" else "⏳ next"
            lines.append(f"\n**Current Workout** ({status_label}):")
            lines.append(f"Week {nw['week']}, Day {nw['day']}: {nw['name'] or 'Untitled'}")
            if nw.get("exercises_preview"):
                lines.append(f"Exercises ({nw['exercises_count']}): {', '.join(nw['exercises_preview'][:3])}")
        elif nw and tw:
            lines.append(f"\n**Next Workout:** W{nw['week']}D{nw['day']} — {nw['name'] or 'Untitled'}")

        # Recent history
        recent = data.get("recent_workouts", [])
        if recent:
            lines.append("\n**Recent Workouts:**")
            for w in recent[:3]:
                today_marker = " ← today" if w.get("is_today") else ""
                date_str = f" ({w['date']}{today_marker})" if w.get('date') else ""
                lines.append(f"- {w['status']} W{w['week']}D{w['day']}: {w['name'] or '-'}{date_str}")

        # Stats
        stats = data.get("stats", {})
        if stats:
            lines.append(f"\n**Stats:** streak {stats.get('streak', 0)}, this week: {stats.get('this_week', '-')}, completion: {stats.get('completion_rate', '-')}")

        # Other plans
        other = data.get("other_plans", [])
        if other:
            other_strs = [f"{p['name']} ({p['status']}, {p['progress']})" for p in other]
            lines.append(f"\n**Other Plans:** {', '.join(other_strs)}")

        return "\n".join(lines)


async def get_plan_navigation(db: AsyncSession, user_id: UUID) -> str:
    """
    Convenience function to generate plan navigation.

    Args:
        db: Database session
        user_id: User identifier

    Returns:
        Formatted navigation string
    """
    navigator = PlanNavigator(db)
    return await navigator.generate(user_id)
