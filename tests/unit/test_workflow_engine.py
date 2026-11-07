"""Unit tests for workflow planning and execution boundaries."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from orb.core.models import Plan, WorkflowStep
from orb.models.goal import Goal
from orb.services.workflow_service import WorkflowService
from orb.storage.database import ORBDatabase
from orb.workflow.engine import WorkflowEngine


class WorkflowEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = WorkflowEngine()

    def test_create_plan_preserves_ai_generated_parameters(self) -> None:
        mock_ai_service = Mock()
        mock_ai_service.generate_json.return_value = {
            "steps": [
                {
                    "name": "Create configuration file",
                    "action_type": "File.Write",
                    "parameters": {"path": "config.json", "content": "ORB configuration"},
                }
            ]
        }
        self.engine.ai_service = mock_ai_service
        plan = self.engine.create_plan("Create a configuration file")
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(
            plan.steps[0].parameters,
            {"path": "config.json", "content": "ORB configuration"},
        )
        self.assertEqual(plan.status, "planned")

    def test_create_plan_uses_supplied_goal_id(self) -> None:
        mock_ai_service = Mock()
        mock_ai_service.generate_json.return_value = {
            "steps": [{"name": "Inspect", "action_type": "Analysis", "parameters": {}}]
        }
        self.engine.ai_service = mock_ai_service
        plan = self.engine.create_plan("Inspect project", goal_id="goal-42")
        self.assertEqual(plan.goal_id, "goal-42")
        self.assertEqual(plan.steps[0].workflow_id, "goal-42")

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
        self.assertFalse(self.engine.execute_step(step))


class WorkflowServiceTests(unittest.TestCase):
    def test_plan_is_persisted_without_claiming_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = ORBDatabase(Path(directory) / "orb.db")
            ai_service = Mock()
            ai_service.generate_json.return_value = {
                "steps": [
                    {"name": "Inspect project", "action_type": "Analysis", "parameters": {}},
                    {"name": "Prepare implementation plan", "action_type": "Planning", "parameters": {}},
                ]
            }
            service = WorkflowService(ai_service, database)
            goal = Goal(title="Build login system", description="Use the existing database.")

            result = service.plan_goal(goal)

            self.assertEqual(result["status"], "PLANNED")
            self.assertGreater(result["execution_id"], 0)
            self.assertEqual(len(result["plan"].steps), 2)
            history = service.get_recent_executions()
            self.assertEqual(history[0]["status"], "PLANNED")
            self.assertEqual(len(service.get_recent_steps()), 2)


if __name__ == "__main__":
    unittest.main()
