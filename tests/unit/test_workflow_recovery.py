from unittest.mock import Mock, patch

from orb.core.models import Plan, WorkflowStep, TaskStatus
from orb.workflow.engine import WorkflowEngine


def make_plan():
    return Plan(
        goal_id="recovery-test",
        steps=[
            WorkflowStep(
                workflow_id="recovery-test",
                sequence=1,
                name="Test action",
                action_type="Test.Action",
            )
        ],
    )


def test_planning_failure_gets_one_retry():
    engine = WorkflowEngine()
    plan = make_plan()

    with patch.object(
        engine, "create_plan", side_effect=[None, plan]
    ) as planner, patch.object(
        engine, "execute_step", return_value=True
    ), patch.object(
        engine, "verify_step", return_value=True
    ):
        assert engine.run("Test goal")

    assert planner.call_count == 2


def test_failed_action_is_not_replayed_automatically():
    engine = WorkflowEngine()
    plan = make_plan()

    with patch.object(
        engine, "create_plan", return_value=plan
    ), patch.object(
        engine, "execute_step", return_value=False
    ) as execute:
        assert not engine.run("Test goal")

    execute.assert_called_once()
    assert plan.steps[0].status is TaskStatus.FAILED


def test_cancellation_prevents_execution():
    engine = WorkflowEngine()
    plan = make_plan()

    def request_cancel(*args, **kwargs):
        engine.cancel()
        return plan

    with patch.object(
        engine, "create_plan", side_effect=request_cancel
    ), patch.object(
        engine, "execute_step"
    ) as execute:
        assert not engine.run("Test goal")

    execute.assert_not_called()
    assert plan.status == "cancelled"

def test_execution_failure_requires_review_without_retry():
    engine = WorkflowEngine()
    plan = make_plan()

    def simulate_failure(step):
        step.execution_status = "execution_failed"
        step.error = "Action may have partially completed"
        return False

    with patch.object(
        engine, "create_plan", return_value=plan
    ) as planner, patch.object(
        engine, "execute_step", side_effect=simulate_failure
    ) as execute:
        assert not engine.run("Test goal")

    execute.assert_called_once()
    planner.assert_called_once()
    assert plan.steps[0].status is TaskStatus.FAILED
    assert plan.status == "needs_review"


def test_unsupported_capability_sets_failed_status_and_step_error():
    from orb.execution import ExecutionService

    execution = ExecutionService(lambda *_: True)
    ai = Mock()
    ai.generate_json.return_value = {
        "steps": [{"name": "Run shell", "action_type": "Shell.Exec", "parameters": {}}]
    }
    engine = WorkflowEngine(ai, execution)

    assert not engine.run("Do unsupported work")
    assert engine.current_plan is not None
    assert engine.current_plan.status == "failed"
    assert engine.current_plan.steps[0].status is TaskStatus.FAILED
    assert "Unsupported capability" in (engine.current_plan.steps[0].error or "")
