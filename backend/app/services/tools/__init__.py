"""Provider-agnostic MCP tool definitions and executor.

The tool implementations are split by domain across plans.py,
workouts.py and health.py (mixin classes). This package re-exports
the combined ``TOOLS`` schema list and the ``ToolExecutor`` facade so
that ``from app.services.tools import TOOLS, ToolExecutor`` keeps
working unchanged.
"""
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .health import HEALTH_TOOLS, HealthToolsMixin
from .plans import PLAN_TOOLS, PlanToolsMixin
from .workouts import WORKOUT_TOOLS, WorkoutToolsMixin

logger = logging.getLogger(__name__)

# Combined provider-agnostic tool schemas (plans + workouts + health).
TOOLS = PLAN_TOOLS + WORKOUT_TOOLS + HEALTH_TOOLS


class ToolExecutor(PlanToolsMixin, WorkoutToolsMixin, HealthToolsMixin):
    """Execute MCP tools against the database.

    Provider-agnostic facade: takes a tool name and arguments,
    dispatches to the matching domain mixin method, and returns the
    result as a dict.
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

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
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
            "get_workout_history": self._get_workout_history,
            "get_user_exercise_progression": self._get_user_exercise_progression,
            "log_exercise_results": self._log_exercise_results,
            "get_body_metrics": self._get_body_metrics,
            "log_body_weight": self._log_body_weight,
            "get_health_profile": self._get_health_profile,
            "get_blood_markers": self._get_blood_markers,
            "log_blood_markers": self._log_blood_markers,
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


__all__ = ["TOOLS", "ToolExecutor"]
