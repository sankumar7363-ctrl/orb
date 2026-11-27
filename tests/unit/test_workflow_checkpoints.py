from unittest.mock import Mock, patch

from orb.execution import ExecutionService
from orb.services.workflow_service import WorkflowService
from orb.storage.database import ORBDatabase


def test_checkpoint_records_completed_and_failed_actions(tmp_path):
    db = ORBDatabase(tmp_path / "orb.db")
    handler = Mock()
    handler.execute.side_effect = ["first result", RuntimeError("Second action failed")]
    handler.verify.return_value = True
    execution = ExecutionService(lambda *_: True)
    execution.register_capability("Test.Action", handler, required_permission="test")
    ai = Mock()
    ai.generate_json.return_value = {
        "steps": [
            {"name": "First", "action_type": "Test.Action", "parameters": {}},
            {"name": "Second", "action_type": "Test.Action", "parameters": {}},
        ]
    }
    with patch("orb.services.workflow_service.ORBDatabase", return_value=db):
        service = WorkflowService(ai, execution)
    assert not service.run_goal("Two actions")
    run = ORBDatabase(tmp_path / "orb.db").fetch_checkpoints()[0]
    assert run["status"] == "needs_review"
    assert run["plan"]["steps"][0]["status"] == "completed"
    assert run["plan"]["steps"][1]["error"] == "Second action failed"
    assert "Second action failed" in service.last_report


def test_checkpoint_failure_prevents_action(tmp_path):
    db = ORBDatabase(tmp_path / "orb.db")
    handler = Mock()
    execution = ExecutionService(lambda *_: True)
    execution.register_capability("Test.Action", handler, required_permission="test")
    ai = Mock()
    ai.generate_json.return_value = {
        "steps": [{"name": "First", "action_type": "Test.Action", "parameters": {}}]
    }
    from orb.workflow.engine import WorkflowEngine
    engine = WorkflowEngine(ai, execution)
    import pytest
    with pytest.raises(OSError):
        engine.run("Test", checkpoint=Mock(side_effect=OSError("Disk unavailable")))
    handler.execute.assert_not_called()


def test_needs_review_status_is_reported(tmp_path):
    db = ORBDatabase(tmp_path / "orb.db")

    handler = Mock()
    handler.execute.side_effect = RuntimeError(
        "Action outcome is uncertain"
    )

    execution = ExecutionService(lambda *_: True)
    execution.register_capability(
        "Test.Action",
        handler,
        required_permission="test",
    )

    ai = Mock()
    ai.generate_json.return_value = {
        "steps": [
            {
                "name": "Risky action",
                "action_type": "Test.Action",
                "parameters": {},
            }
        ]
    }

    with patch(
        "orb.services.workflow_service.ORBDatabase",
        return_value=db,
    ):
        service = WorkflowService(ai, execution)

    assert not service.run_goal("Test uncertain action")
    assert service._engine.current_plan.status == "needs_review"
    assert service.last_report.startswith("Needs Review")
    handler.execute.assert_called_once()
