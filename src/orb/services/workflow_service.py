"""
=============================================================
ORB Platform
Workflow Service

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from __future__ import annotations

from orb.logging import get_logger
from orb.services.ai_service import AIService
from orb.workflow.engine import WorkflowEngine
from orb.storage.database import ORBDatabase


class WorkflowService:
    """Manages workflow planning, execution, and persistence."""

    def __init__(self, ai_service: AIService) -> None:
        self._logger = get_logger("service.workflow")
        self._engine = WorkflowEngine(ai_service)
        self._db = ORBDatabase()

    def initialize(self) -> None:
        self._logger.info("Workflow Service initialized.")

    def shutdown(self) -> None:
        self._logger.info("Workflow Service shutdown.")

    def start(self) -> None:
        self._logger.info(
            "Workflow Service started. ORB is ready to accept goals."
        )

    def stop(self) -> None:
        self._logger.info("Workflow Service stopped.")

    def run_goal(self, goal_text: str) -> bool:
        """Run a goal through the workflow engine and persist its result."""

        self._logger.info(
            "Running goal through workflow engine: '%s'",
            goal_text,
        )

        success = self._engine.run(goal_text)

        current_plan = self._engine.current_plan

        steps_data = [
            {
                "sequence": step.sequence,
                "name": step.name,
                "action_type": step.action_type,
                "status": (
                    step.status.value
                    if hasattr(step.status, "value")
                    else str(step.status)
                ),
            }
            for step in current_plan.steps
        ] if current_plan else []

        status_str = "COMPLETED" if success else "FAILED"

        execution_id = self._db.save_execution(
            goal=goal_text,
            status=status_str,
            steps=steps_data,
        )

        if execution_id == -1:
            self._logger.error(
                "Workflow execution finished, but execution history "
                "could not be saved."
            )
        else:
            self._logger.info(
                "Workflow execution history saved with ID: %d",
                execution_id,
            )

        return success