"""
=============================================================
ORB Platform
Workflow Service

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from __future__ import annotations

from orb.core.models import Plan
from orb.logging import get_logger
from orb.models.goal import Goal
from orb.services.ai_service import AIService
from orb.workflow.engine import WorkflowEngine
from orb.storage.database import ORBDatabase


class WorkflowService:
    """Manages workflow planning, execution history, and persistence."""

    def __init__(
        self,
        ai_service: AIService,
        database: ORBDatabase | None = None,
    ) -> None:
        self._logger = get_logger("service.workflow")
        self._engine = WorkflowEngine(ai_service)
        self._db = database or ORBDatabase()

    def initialize(self) -> None:
        self._logger.info("Workflow Service initialized.")

    def shutdown(self) -> None:
        self._logger.info("Workflow Service shutdown.")

    def start(self) -> None:
        self._logger.info("Workflow Service started. ORB is ready to accept goals.")

    def stop(self) -> None:
        self._logger.info("Workflow Service stopped.")

    def plan_goal(self, goal: Goal) -> dict | None:
        """Generate and persist a proposal without executing its steps."""
        goal_text = goal.description.strip() or goal.title
        plan = self._engine.create_plan(goal_text, goal_id=goal.id)
        if plan is None:
            return None

        steps_data = [
            {
                "sequence": step.sequence,
                "name": step.name,
                "action_type": step.action_type,
                "status": step.status.value,
            }
            for step in plan.steps
        ]
        execution_id = self._db.save_execution(
            goal=goal.title,
            status="PLANNED",
            steps=steps_data,
        )
        if execution_id < 0:
            raise RuntimeError("The plan was generated but could not be saved to history.")

        self._logger.info(
            "Plan %s for goal '%s' saved as workflow record %d.",
            plan.id,
            goal.title,
            execution_id,
        )
        return {
            "plan": plan,
            "execution_id": execution_id,
            "status": "PLANNED",
        }

    def get_recent_executions(self, limit: int = 8) -> list[dict]:
        """Return recent planned or executed workflow records."""
        return self._db.fetch_recent_executions(limit=limit)

    def get_recent_steps(self, limit: int = 30) -> list[dict]:
        """Return recent workflow steps for the Tasks view."""
        return self._db.fetch_recent_execution_steps(limit=limit)

    def run_goal(self, goal_text: str) -> bool:
        """Run the goal through the current execution handlers and save its result."""
        self._logger.info("Running goal through workflow engine: '%s'", goal_text)
        success = self._engine.run(goal_text)
        current_plan = self._engine.current_plan

        steps_data = [
            {
                "sequence": step.sequence,
                "name": step.name,
                "action_type": step.action_type,
                "status": step.status.value,
            }
            for step in current_plan.steps
        ] if current_plan else []

        execution_id = self._db.save_execution(
            goal=goal_text,
            status="COMPLETED" if success else "FAILED",
            steps=steps_data,
        )
        if execution_id < 0:
            self._logger.error("Workflow record could not be saved to history.")
        else:
            self._logger.info("Workflow history saved with ID: %d", execution_id)
        return success
