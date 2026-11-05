
"""Unit tests for ORB workflow engine."""

import unittest

from unittest.mock import Mock, patch

from orb.workflow.engine import WorkflowEngine
from orb.core.models import Plan, WorkflowStep


class WorkflowEngineTests(unittest.TestCase):

    def setUp(self) -> None:
        self.engine = WorkflowEngine()

    def test_create_plan_preserves_ai_generated_parameters(self) -> None:
        ai_response = {
            "steps": [
                {
                    "name": "Create configuration file",
                    "action_type": "File.Write",
                    "parameters": {
                        "path": "config.json",
                        "content": "ORB configuration",
                    },
                }
            ]
        }

        mock_ai_service = Mock()
        mock_ai_service.generate_json.return_value = ai_response
        self.engine.ai_service = mock_ai_service

        plan = self.engine.create_plan("Create a configuration file")

        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(
            plan.steps[0].parameters,
            {
                "path": "config.json",
                "content": "ORB configuration",
            },
        )

    def test_run_fails_when_verification_fails(self) -> None:
        plan = Plan(
            goal_id="goal-1",
            steps=[
                WorkflowStep(
                    workflow_id="workflow-1",
                    sequence=1,
                    name="Create configuration file",
                    action_type="File.Write",
                )
            ],
        )

        with (
            patch.object(self.engine, "create_plan", return_value=plan),
            patch.object(self.engine, "execute_step", return_value=True),
            patch.object(self.engine, "verify_step", return_value=False),
        ):
            success = self.engine.run("Create a configuration file")

        self.assertFalse(success)

    def test_execute_step_returns_false_when_no_handler_exists(self) -> None:
        step = WorkflowStep(
            workflow_id="workflow-1",
            sequence=1,
            name="Create configuration file",
            action_type="File.Write",
        )

        success = self.engine.execute_step(step)

        self.assertFalse(success)


if __name__ == "__main__":
    unittest.main()
