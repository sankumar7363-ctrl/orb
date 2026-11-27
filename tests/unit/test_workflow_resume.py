from unittest.mock import Mock

from orb.core.models import Plan, WorkflowStep, TaskStatus, VerificationStatus
from orb.execution import ExecutionService
from orb.workflow.engine import WorkflowEngine


def test_resume_preserves_completed_actions_and_executes_pending():
    handler = Mock()
    handler.verify.return_value = True
    execution = ExecutionService(lambda *_: True)
    execution.register_capability("Test", handler, required_permission="test")
    plan = Plan(goal_id="goal", steps=[
        WorkflowStep(workflow_id="flow", sequence=1, name="Done", action_type="Test",
                     status=TaskStatus.COMPLETED, verification_status=VerificationStatus.PASSED),
        WorkflowStep(workflow_id="flow", sequence=2, name="Next", action_type="Test",
                     status=TaskStatus.CANCELLED),
    ])
    engine = WorkflowEngine(None, execution)
    assert engine.run("Resume", resume_plan=plan)
    assert handler.execute.call_count == 1
    assert all(step.status is TaskStatus.COMPLETED for step in plan.steps)


def test_resume_does_not_repeat_uncertain_action():
    handler = Mock()
    execution = ExecutionService(lambda *_: True)
    execution.register_capability("Test", handler, required_permission="test")
    plan = Plan(goal_id="goal", steps=[
        WorkflowStep(workflow_id="flow", sequence=1, name="Uncertain", action_type="Test",
                     status=TaskStatus.RUNNING),
    ])
    engine = WorkflowEngine(None, execution)
    assert not engine.run("Resume", resume_plan=plan)
    handler.execute.assert_not_called()
    assert plan.status == "needs_review"
