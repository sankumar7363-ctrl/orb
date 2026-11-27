import os
from unittest.mock import Mock, patch

import pytest

PySide6 = pytest.importorskip("PySide6.QtWidgets")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from orb.gui.__main__ import LLMExecutionWorker, ORBLLMDashboard


def _qt_app():
    return QApplication.instance() or QApplication([])


def test_llm_worker_falls_back_to_chat_when_router_rejects_output():
    _qt_app()
    kernel = Mock()
    kernel.ai_service.generate_json.return_value = {"mode": "execute_shell"}
    kernel.ai_service.generate.return_value = "I cannot run shell commands."
    kernel.execution_service.capability_catalog.return_value = []

    worker = LLMExecutionWorker(kernel, "Do something unclear")
    outputs = []
    worker.finished_signal.connect(outputs.append)
    worker.run()

    kernel.workflow_service.run_goal.assert_not_called()
    assert outputs == ["I cannot run shell commands."]


def test_dashboard_pauses_wake_word_for_speech_output_and_ignores_blank_audio(tmp_path):
    app = _qt_app()
    fake_kernel = Mock()
    fake_kernel.is_running.return_value = True
    fake_kernel.configuration.get.return_value = False
    fake_kernel.voice_service.is_wake_word_active = True

    with patch("orb.gui.__main__.ORBKernel", return_value=fake_kernel):
        window = ORBLLMDashboard()

    try:
        window.on_voice_transcript("[BLANK_AUDIO] [NOISE]", None)
        assert window.msg_input.text() == ""

        with patch("orb.gui.__main__.WakeWordHandoffWorker") as handoff_cls:
            handoff = Mock()
            handoff.isRunning.return_value = False
            handoff_cls.return_value = handoff

            window.start_speech_output("Hello, I am ORB.")

            assert window.resume_wake_word is True
            assert window._pending_speech == "Hello, I am ORB."
            handoff.start.assert_called_once()
    finally:
        window.closing = True
        window.close()
        app.processEvents()
