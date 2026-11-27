from unittest.mock import Mock

import pytest

from orb.services.interaction import InteractionRouter
from orb.services.project_context import ProjectContext
from orb.workflow.engine import WorkflowEngine


def test_router_uses_catalog_for_polite_requests():
    ai = Mock()
    ai.generate_json.return_value = {"mode": "workflow", "message": ""}
    execution = Mock()
    execution.capability_catalog.return_value = [{"name": "App.Open"}]
    assert InteractionRouter(ai, execution).route(
        "Could you open Excel and then open Word?"
    )["mode"] == "workflow"
    assert "App.Open" in ai.generate_json.call_args.kwargs["prompt"]


@pytest.mark.parametrize(("request_text", "capability", "parameters"), [
    ("Please open Visual Studio Code.", "App.Open", {"application": "vs code"}),
    ("Open Chrome.", "App.Open", {"application": "chrome"}),
    ("Open File Manager", "App.Open", {"application": "file explorer"}),
    ("Open YouTube.", "Browser.Open", {"url": "https://www.youtube.com/"}),
    ("Please open https://example.org/watch?v=42", "Browser.Open",
     {"url": "https://example.org/watch?v=42"}),
    ("Search in the browser for Python docs", "Browser.Search", {"query": "Python docs"}),
])
def test_desktop_commands_route_and_plan_without_model(request_text, capability, parameters):
    ai = Mock()
    execution = Mock()
    assert InteractionRouter(ai, execution).route(request_text)["mode"] == "workflow"

    plan = WorkflowEngine(ai, execution).create_plan(request_text)
    assert len(plan.steps) == 1
    assert plan.steps[0].action_type == capability
    assert plan.steps[0].parameters == parameters
    ai.generate_json.assert_not_called()


@pytest.mark.parametrize("request_text", ["Open XO", "Open your view."])
def test_unknown_open_target_asks_for_clarification(request_text):
    ai = Mock()
    route = InteractionRouter(ai, Mock()).route(request_text)
    assert route["mode"] == "clarify"
    assert request_text[5:].rstrip(".") in route["message"]
    ai.generate_json.assert_not_called()


def test_greeting_skips_intent_classification():
    ai = Mock()
    assert InteractionRouter(ai, Mock()).route("Hello, ORB!")["mode"] == "chat"
    ai.generate_json.assert_not_called()


def test_router_rejects_invalid_model_output():
    ai = Mock()
    ai.generate_json.return_value = {"mode": "execute_shell"}
    execution = Mock()
    execution.capability_catalog.return_value = []
    with pytest.raises(ValueError):
        InteractionRouter(ai, execution).route("Do something")


@pytest.mark.parametrize("request_text", [
    "What is your name?",
    "What is Excel used for?",
    "How do I open Excel?",
    "Could you explain what Brave does?",
    "Can you tell me how to open Chrome?",
])
def test_informational_questions_route_to_chat_without_execution(request_text):
    ai = Mock()
    route = InteractionRouter(ai, Mock()).route(request_text)
    assert route["mode"] == "chat"
    ai.generate_json.assert_not_called()


@pytest.mark.parametrize(("request_text", "capability", "parameters"), [
    ("Open Excel", "App.Open", {"application": "excel"}),
    ("Could you open Excel?", "App.Open", {"application": "excel"}),
    ("Open Microsoft Excel", "App.Open", {"application": "excel"}),
    ("Open Brave", "App.Open", {"application": "brave"}),
    ("Could you open Brave?", "App.Open", {"application": "brave"}),
    ("Search the web for Python tutorials", "Browser.Search", {"query": "Python tutorials"}),
    ("Can you search the web for Python tutorials?", "Browser.Search", {"query": "Python tutorials"}),
])
def test_polite_and_supported_app_commands_route_and_plan(request_text, capability, parameters):
    ai = Mock()
    execution = Mock()
    assert InteractionRouter(ai, execution).route(request_text)["mode"] == "workflow"

    plan = WorkflowEngine(ai, execution).create_plan(request_text)
    assert plan is not None
    assert len(plan.steps) == 1
    assert plan.steps[0].action_type == capability
    assert plan.steps[0].parameters == parameters
    ai.generate_json.assert_not_called()


@pytest.mark.parametrize("request_text", ["Open", "Open.", "Launch", "Open the app"])
def test_incomplete_open_requests_clarify_without_model(request_text):
    ai = Mock()
    route = InteractionRouter(ai, Mock()).route(request_text)
    assert route["mode"] == "clarify"
    assert route["message"].strip()
    ai.generate_json.assert_not_called()


@pytest.mark.parametrize("bad_output", [
    None,
    ["workflow"],
    {},
    {"mode": "clarify"},
    {"mode": "clarify", "message": "   "},
    {"mode": "workflow"},
])
def test_router_rejects_malformed_or_unexecutable_ai_classifications(bad_output):
    ai = Mock()
    ai.generate_json.return_value = bad_output
    execution = Mock()
    execution.capability_catalog.return_value = []
    with pytest.raises(ValueError):
        InteractionRouter(ai, execution).route("Do something ambiguous")


def test_context_is_empty_until_project_selected_and_reads_bounded_documents(tmp_path):
    context = ProjectContext()
    assert context.snapshot() == {}
    (tmp_path / "README.md").write_text("a" * 9000, encoding="utf-8")
    (tmp_path / ".env").write_text("private", encoding="utf-8")
    context.select(str(tmp_path))
    snapshot = context.snapshot()
    assert len(snapshot["documents"]["README.md"]) == 6000
    assert ".env" not in snapshot["entries"]
