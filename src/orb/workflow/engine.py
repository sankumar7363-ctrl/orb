
"""
=============================================================
ORB Platform
Workflow Engine

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from __future__ import annotations

from typing import Any

from orb.logging import get_logger
from orb.core.models import (
    Plan,
    WorkflowStep,
    TaskStatus,
    VerificationStatus,
)
from orb.services.ai_service import AIService


class WorkflowEngine:
    """Manages AI planning, execution, and verification."""

    def __init__(self, ai_service: AIService | None = None) -> None:
        self._logger = get_logger("workflow.engine")
        self.ai_service = ai_service
        self.current_plan: Plan | None = None

    def _get_ai_plan_steps(self, goal_text: str) -> list[dict[str, Any]]:
        """Generate a structured proposal using the shared AI service."""
        if self.ai_service is None:
            raise RuntimeError("AI Service is not available for planning.")

        prompt = (
            "Break down the user's goal into a logical sequence of steps. "
            "Return a JSON object containing a 'steps' array. "
            "Each step must contain 'name', 'action_type', and 'parameters'. "
            "These steps are proposals only. Do not claim they have been executed. "
            "Use only proposed actions; do not invent that a tool has run.\n\n"
            f"User Goal: {goal_text}"
        )

        self._logger.info("Requesting workflow plan from AI Service.")
        result = self.ai_service.generate_json(
            prompt=prompt,
            system_prompt=(
                "You are ORB, a goal-oriented AI planning system. "
                "Generate clear, structured, safe workflow plans. "
                "Never claim execution has occurred."
            ),
        )

        steps = result.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError("AI returned no valid workflow steps.")

        for step in steps:
            if not isinstance(step, dict):
                raise ValueError("AI returned an invalid workflow step.")
            if not isinstance(step.get("name"), str) or not step["name"].strip():
                raise ValueError("Workflow step is missing a valid name.")
            if not isinstance(step.get("action_type"), str) or not step["action_type"].strip():
                raise ValueError("Workflow step is missing an action type.")
            if not isinstance(step.get("parameters", {}), dict):
                raise ValueError("Workflow step parameters must be an object.")

        self._logger.info("AI generated %d workflow steps.", len(steps))
        return steps

    def create_plan(self, goal_text: str, goal_id: str = "1") -> Plan | None:
        """Create and retain a structured plan; this does not execute it."""
        self.current_plan = None
        try:
            raw_steps = self._get_ai_plan_steps(goal_text)
            normalized_steps = [
                WorkflowStep(
                    workflow_id=goal_id,
                    sequence=index,
                    name=raw["name"].strip(),
                    action_type=raw["action_type"].strip(),
                    parameters=raw.get("parameters", {}),
                    status=TaskStatus.PENDING,
                )
                for index, raw in enumerate(raw_steps, start=1)
            ]
            self.current_plan = Plan(
                goal_id=goal_id,
                steps=normalized_steps,
                status="planned",
            )
            return self.current_plan
        except Exception as error:
            self._logger.error("Workflow planning failed: %s", error)
            return None

    def execute_step(self, step: WorkflowStep) -> bool:
        """Execute a step only when a capability handler is registered."""
        self._logger.warning(
            "No execution handler registered for action type '%s'. "
            "Step was not executed.",
            step.action_type,
        )
        return False

    def verify_step(self, step: WorkflowStep) -> bool:
        """Report that verification is unavailable until implemented."""
        self._logger.warning(
            "No verification handler registered for step '%s'.",
            step.name,
        )
        return False

    def run(self, goal_text: str) -> bool:
        """Run the plan-execute-verify lifecycle where handlers exist."""
        self._logger.info("Planner generating plan for goal: '%s'", goal_text)
        plan = self.create_plan(goal_text)
        if plan is None or not plan.steps:
            self._logger.error("No valid workflow plan was generated.")
            return False

        self._logger.info("Plan created successfully with %d steps.", len(plan.steps))
        for step in plan.steps:
            self._logger.info("Processing step [%d]: %s", step.sequence, step.name)
            if not self.execute_step(step):
                step.status = TaskStatus.FAILED
                self._logger.error("Step [%d] was not executed.", step.sequence)
                return False

            step.status = TaskStatus.COMPLETED
            if not self.verify_step(step):
                step.verification_status = VerificationStatus.FAILED_SAFE
                step.status = TaskStatus.FAILED
                self._logger.error("Verification failed for step: %s", step.name)
                return False
            step.verification_status = VerificationStatus.PASSED

        self._logger.info("Workflow execution finished for goal: '%s'", goal_text)
        return True
