"""
=============================================================
ORB Platform
Workflow Service

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from __future__ import annotations
from threading import Lock
from uuid import uuid4

from orb.core.models import WorkflowStep, Plan
from orb.logging import get_logger
from orb.execution import ExecutionService
from orb.services.ai_service import AIService
from orb.workflow.engine import WorkflowEngine
from orb.storage.database import ORBDatabase
from orb.services.project_context import ProjectContext


class WorkflowService:
    """Manages workflow planning, execution, and persistence."""

    def __init__(
        self,
        ai_service: AIService,
        execution_service: ExecutionService,
    ) -> None:
        self._logger = get_logger("service.workflow")
        self.execution_service = execution_service
        self._engine = WorkflowEngine(ai_service, execution_service)
        self._db = ORBDatabase()
        self.project_context = ProjectContext()
        self._engine.context_provider = self.project_context.snapshot
        self._run_lock = Lock()
        self.last_report = ""

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

    @property
    def current_steps(self) -> tuple[WorkflowStep, ...]:
        plan = self._engine.current_plan
        return tuple(plan.steps) if plan else ()

    def recent_runs(self) -> list[dict]:
        return self._db.fetch_recent_executions()

    def cancel(self):
        self._engine.cancel()

    def checkpoints(self):
        return self._db.fetch_checkpoints()

    def run_goal(self, goal_text: str, resume_plan=None, run_id=None) -> bool:
        """Run a goal through the workflow engine and persist its result."""
        if not self._run_lock.acquire(blocking=False):
            raise RuntimeError("A workflow is already running.")
        try:
            return self._run_goal(goal_text, resume_plan, run_id)
        finally:
            self._run_lock.release()

    def resume(self, run_id: str):
        record = self._db.get_checkpoint(run_id)
        if record is None or not record["plan"]:
            raise ValueError("This workflow has no saved plan to resume.")
        plan = Plan.model_validate(record["plan"])
        return self.run_goal(record["goal"], resume_plan=plan, run_id=run_id)

    def _run_goal(self, goal_text: str, resume_plan=None, run_id=None) -> bool:

        self._logger.info(
            "Running goal through workflow engine: '%s'",
            goal_text,
        )

        run_id = run_id or str(uuid4())
        self.last_report = "Planning"
        self._db.checkpoint(run_id, goal_text, "planning", resume_plan)

        def checkpoint(plan):
            status = plan.status if plan is not None else "failed"
            self._db.checkpoint(run_id, goal_text, status, plan)

        try:
            success = self._engine.run(goal_text, checkpoint=checkpoint, resume_plan=resume_plan)
        except Exception as error:
            self.last_report = f"Workflow interrupted: {error}"
            self._db.checkpoint(
                run_id, goal_text, "interrupted", self._engine.current_plan, str(error)
            )
            raise

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

        status_str = "Completed" if success else "Failed"

        if current_plan:
            if current_plan.status == "cancelled":
                status_str = "Cancelled"
            elif current_plan.status == "needs_review":
                status_str = "Needs Review"

        self.last_report = status_str
        if current_plan:
            for step in current_plan.steps:
                self.last_report += f"\n{step.sequence}. {step.name}: {step.status.value}"
                if step.error:
                    self.last_report += f" — {step.error}"
        else:
            self.last_report += "\nNo executable plan was produced for the available tools."

        execution_id = self._db.save_execution(
            goal=goal_text,
            status=status_str,
            steps=steps_data,
        )

        if execution_id == -1:
            self.last_report += "\nThe final history summary could not be saved."
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
