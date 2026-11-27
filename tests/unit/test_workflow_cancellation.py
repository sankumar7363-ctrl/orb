from unittest.mock import Mock

from orb.execution import ExecutionService
from orb.workflow.engine import WorkflowEngine


def test_cancel_during_approval_prevents_execution():
    handler = Mock()
    service = ExecutionService(lambda *_: True)
    service.register_capability("Test.Action", handler, required_permission="test", requires_approval=True)
    ai = Mock()
    ai.generate_json.return_value = {
        "steps": [{"name": "Test", "action_type": "Test.Action", "parameters": {}}]
    }
    engine = WorkflowEngine(ai, service)

    def approve(*_):
        engine.cancel()
        return True

    service.set_approval_handler(approve)
    assert not engine.run("Test cancellation")
    handler.execute.assert_not_called()
    assert engine.current_plan.status == "cancelled"


def test_cancel_after_action_preserves_completed_step():
    handler = Mock()
    service = ExecutionService(lambda *_: True)
    service.register_capability("Test.Action", handler, required_permission="test")
    ai = Mock()
    ai.generate_json.return_value = {
        "steps": [
            {"name": "First", "action_type": "Test.Action", "parameters": {}},
            {"name": "Second", "action_type": "Test.Action", "parameters": {}},
        ]
    }
    engine = WorkflowEngine(ai, service)
    handler.execute.side_effect = lambda _: engine.cancel()
    handler.verify.return_value = True
    assert not engine.run("Test cancellation")
    assert handler.execute.call_count == 1
    assert engine.current_plan.steps[0].status.value == "completed"
    assert engine.current_plan.steps[1].status.value == "cancelled"
