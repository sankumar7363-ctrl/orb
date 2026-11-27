"""
=============================================================
ORB Platform - Operational Reasoning Platform
Direct Ollama LLM-Integrated AI Assistant Dashboard

Author: Santosh Kumar
=============================================================
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QThread, Signal, QObject

from orb.gui.dashboard import DashboardView
from orb.core.kernel import ORBKernel
from orb.gui.approval import QtApprovalBridge
from orb.storage.memory import MemoryStore
from orb.services.interaction import InteractionRouter
from orb.voice.speech_recognition import is_valid_speech_transcript



class LLMExecutionWorker(QThread):
    """Background worker using ORB's central AI and workflow services."""

    log_signal = Signal(str)
    goal_started = Signal(str)
    goal_finished = Signal(bool, object)
    finished_signal = Signal(str)

    def __init__(self, kernel: ORBKernel, query: str, resume_id=None):
        super().__init__()
        self.kernel = kernel
        self.query = query.strip()
        self.resume_id = resume_id

    def run(self):
        is_action_task = False
        try:
            if self.resume_id:
                self.goal_started.emit(self.query)
                success = self.kernel.workflow_service.resume(self.resume_id)
                steps = tuple(
                    (step.name, step.status.value)
                    for step in self.kernel.workflow_service.current_steps
                )
                self.goal_finished.emit(success, steps)
                self.finished_signal.emit(self.kernel.workflow_service.last_report)
                return
            q_lower = self.query.lower()

            route = {"mode": "chat"}
            if not (
                q_lower.startswith("remember ")
                or q_lower.rstrip("?.!") in ("show my notes", "what do you remember")
            ):
                try:
                    route = InteractionRouter(
                        self.kernel.ai_service, self.kernel.execution_service
                    ).route(self.query)
                except ValueError:
                    route = {"mode": "chat"}
                is_action_task = route["mode"] == "workflow"

            if q_lower.startswith("remember "):
                MemoryStore().save(self.query[len("remember "):])
                response = "I saved that note. You can review or delete it in Memory."
            elif q_lower.rstrip("?.!") in ("show my notes", "what do you remember"):
                notes = MemoryStore().notes()
                response = "\n".join(f"• {note}" for _, note in notes[:10])
                if not response:
                    response = "You have no saved notes."
                elif len(notes) > 10:
                    response += "\nOpen Memory to see all saved notes."
            elif route["mode"] == "clarify":
                response = route["message"]
            elif is_action_task:
                self.goal_started.emit(self.query)
                self.log_signal.emit(
                    f"⚙️ Processing workflow goal: '{self.query}'..."
                )

                success = self.kernel.workflow_service.run_goal(
                    self.query
                )

                steps = tuple(
                    (step.name, step.status.value)
                    for step in self.kernel.workflow_service.current_steps
                )
                self.goal_finished.emit(success, steps)

                if success:
                    response = (
                        f"Workflow for '{self.query}' completed."
                    )
                    if any(
                        step.action_type in ("Browser.Open", "Browser.Search", "File.Open")
                        for step in self.kernel.workflow_service.current_steps
                    ):
                        response += (
                            " Windows accepted the opening requests. "
                            "Page and document contents have not been inspected."
                        )
                else:
                    response = self.kernel.workflow_service.last_report

            else:
                self.log_signal.emit(
                    "🧠 Processing request through ORB AI Service..."
                )

                response = self.kernel.ai_service.generate(
                    prompt=self.query,
                    system_prompt=(
                        "You are ORB, a helpful local AI assistant. "
                        "Respond clearly, accurately, and concisely. "
                        "ORB's workflow tools can launch supported Windows apps, "
                        "open websites and local files, and search the web. "
                        "Do not claim to have performed actions unless "
                        "they were actually executed and verified."
                    ),
                )

            self.finished_signal.emit(response)

        except Exception as error:
            if is_action_task:
                self.goal_finished.emit(False, ())
            error_message = f"❌ ORB Error: {error}"
            self.finished_signal.emit(error_message)

class WakeWordBridge(QObject):
    """Forward wake-word detections safely to the GUI thread."""

    detected = Signal(float)
    ready = Signal()
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def on_detected(self, score: float) -> None:
        self.detected.emit(score)

    def on_ready(self) -> None:
        self.ready.emit()

    def on_error(self, message: str) -> None:
        self.failed.emit(message)

class VoiceInputWorker(QThread):
    """Capture and transcribe one utterance without blocking the GUI."""

    transcript_signal = Signal(str, object)
    error_signal = Signal(str)

    def __init__(self, kernel: ORBKernel):
        super().__init__()
        self.kernel = kernel

    def run(self):
        try:
            result = self.kernel.voice_service.listen_once()
            if not result.text:
                self.error_signal.emit("No speech was recognized. Please try again.")
                return

            threshold = self.kernel.voice_service.minimum_confidence
            if result.confidence is not None and result.confidence < threshold:
                self.error_signal.emit(
                    f"Speech was unclear (confidence {result.confidence:.2f}). "
                    "Please try again."
                )
                return

            self.transcript_signal.emit(result.text, result.confidence)
        except Exception as error:
            self.error_signal.emit(str(error))

class WakeWordHandoffWorker(QThread):
    """Release the wake-word microphone without blocking the GUI."""

    ready = Signal()
    error_signal = Signal(str)

    def __init__(self, kernel):
        super().__init__()
        self.kernel = kernel

    def run(self):
        try:
            self.kernel.voice_service.disable_wake_word()

            if self.kernel.voice_service.is_wake_word_active:
                self.error_signal.emit(
                    "Wake-word microphone was not released."
                )
                return

            self.ready.emit()

        except Exception as error:
            self.error_signal.emit(str(error))

class SpeechOutputWorker(QThread):
    """Generate and play an AI response using the local Piper voice."""

    error_signal = Signal(str)

    def __init__(self, kernel: ORBKernel, text: str):
        super().__init__()
        self.kernel = kernel
        self.text = text

    def run(self):
        try:
            self.kernel.voice_service.speak(self.text)
        except Exception as error:
            self.error_signal.emit(str(error))


class ORBLLMDashboard(QMainWindow):
    """LLM-Integrated Dashboard Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ORB — Operational Reasoning Platform")
        self.resize(1450, 800)
        self.worker = None

        try:
            self.kernel = ORBKernel()
            self.kernel.start()
        except Exception as e:
            print(f"Kernel init warning: {e}")

        self.voice_input_worker = None
        self.speech_output_worker = None
        self.wake_handoff_worker = None
        self._pending_speech: str | None = None
        self.resume_wake_word = False
        self.submit_wake_transcript = False
        self.voice_conversation = False
        self.closing = False
        self.voice_output_enabled = True
        self.wake_word_bridge = WakeWordBridge(self)
        self.wake_word_bridge.detected.connect(self.on_wake_word_detected)
        self.wake_word_bridge.ready.connect(self.on_wake_word_ready)
        self.wake_word_bridge.failed.connect(self.on_wake_word_error)

        self.init_ui()
        self.approval_bridge = QtApprovalBridge(self)
        self.kernel.execution_service.set_approval_handler(
            self.approval_bridge.request_approval
        )
        if self.kernel.configuration.get("voice.wake_word.enabled", False):
            self.arm_wake_word()

    def arm_wake_word(self):
        if self.view.activity_state.text() in ("Idle", "Voice input"):
            self.view.set_activity("Idle", "Starting wake-word detection…")
        try:
            self.kernel.voice_service.enable_wake_word(
                self.wake_word_bridge.on_detected,
                on_ready=self.wake_word_bridge.on_ready,
                on_error=self.wake_word_bridge.on_error,
            )
        except Exception as error:
            self.on_wake_word_error(str(error))

    def on_wake_word_ready(self):
        if not self.closing:
            self.append_log('Voice ready. Say “ORB” to start.')
            if self.view.activity_state.text() in ("Idle", "Voice input"):
                self.view.set_activity("Idle", 'Waiting for “ORB”.')

    def on_wake_word_error(self, message):
        if not self.closing:
            self.append_log(f"Wake-word listener error: {message}")
            if self.view.activity_state.text() == "Idle":
                self.view.set_activity("Voice unavailable", message)

    def init_ui(self):
        self.view = DashboardView(self)
        self.setCentralWidget(self.view)
        self.chat_display = self.view.chat_display
        self.msg_input = self.view.msg_input
        self.mic_button = self.view.mic_button
        self.voice_output_button = self.view.voice_output_button

    def send_message(self, *, from_wake_word=False):
        text = self.msg_input.text().strip()
        if not text:
            return
        if self.worker is not None and self.worker.isRunning():
            self.view.set_activity("Working", "Finish the current request before sending another.")
            return
        self.voice_conversation = from_wake_word
        self.msg_input.clear()
        self.view.set_activity("Working", "Understanding request…")

        self.view.append_chat(f"You: {text}")

        self.worker = LLMExecutionWorker(self.kernel, text)
        self.worker.log_signal.connect(self.append_log)
        self.worker.goal_started.connect(self.view.start_goal)
        self.worker.goal_finished.connect(self.view.finish_goal)
        self.worker.finished_signal.connect(self.on_response_finished)
        self.worker.start()

    def resume_workflow(self, run_id, goal):
        if self.worker is not None and self.worker.isRunning():
            self.view.set_activity("Working", "Finish the current request before resuming.")
            return
        self.voice_conversation = False
        self.worker = LLMExecutionWorker(self.kernel, goal, resume_id=run_id)
        self.worker.goal_started.connect(self.view.start_goal)
        self.worker.goal_finished.connect(self.view.finish_goal)
        self.worker.finished_signal.connect(self.on_response_finished)
        self.worker.log_signal.connect(self.append_log)
        self.worker.start()

    def append_log(self, message: str):
        """Append an execution log to the chat display."""
        self.view.append_chat(message)

    def on_response_finished(self, response: str):
        """Handle completion of an AI response and optionally speak it."""
        self.view.append_chat(f"ORB: {response}")
        self.view.set_activity("Idle", "Response ready.")
        if self.voice_output_enabled and response.strip():
            self.start_speech_output(response)
        else:
            self.end_voice_conversation()

    def on_wake_word_detected(self, score: float):
        """Start microphone handoff after ORB wake-word detection."""
        if self.closing or self.msg_input.text().strip() or any(
            worker is not None and worker.isRunning()
            for worker in (self.worker, self.speech_output_worker)
        ):
            return

        if self.wake_handoff_worker is not None:
            if self.wake_handoff_worker.isRunning():
                return

        if self.voice_input_worker is not None:
            if self.voice_input_worker.isRunning():
                return

        self.append_log(
            f"ORB wake word detected (confidence {score:.2f})."
        )

        self.wake_handoff_worker = WakeWordHandoffWorker(self.kernel)
        self.resume_wake_word = True
        self.wake_handoff_worker.ready.connect(self.start_wake_voice_input)
        self.wake_handoff_worker.error_signal.connect(self.on_voice_error)
        self.wake_handoff_worker.start()

    def start_wake_voice_input(self):
        self.start_voice_input(from_wake_word=True)

    def start_voice_input(self, *, from_wake_word=False):
        """Start one explicit microphone capture in a background thread."""
        if self.closing:
            return
        if not self.kernel.is_running():
            self.append_log("Voice input is unavailable because ORB is not running.")
            return
        if self.voice_input_worker is not None and self.voice_input_worker.isRunning():
            return
        if self.wake_handoff_worker is not None and self.wake_handoff_worker.isRunning():
            return
        if self.speech_output_worker is not None and self.speech_output_worker.isRunning():
            self.kernel.voice_service.stop_speaking()

        # Release the wake-word microphone off the GUI thread before Whisper records.
        if self.kernel.voice_service.is_wake_word_active:
            self.resume_wake_word = True
            self.mic_button.setEnabled(False)
            self.wake_handoff_worker = WakeWordHandoffWorker(self.kernel)
            self.wake_handoff_worker.ready.connect(
                lambda fw=from_wake_word: self._begin_voice_capture(from_wake_word=fw)
            )
            self.wake_handoff_worker.error_signal.connect(self._on_handoff_error)
            self.wake_handoff_worker.start()
            return

        self._begin_voice_capture(from_wake_word=from_wake_word)

    def _on_handoff_error(self, message: str):
        self.mic_button.setEnabled(True)
        self.on_voice_error(message)

    def _begin_voice_capture(self, *, from_wake_word: bool):
        if self.closing or not self.kernel.is_running():
            self.mic_button.setEnabled(True)
            return
        if self.voice_input_worker is not None and self.voice_input_worker.isRunning():
            return
        if self.kernel.voice_service.is_wake_word_active:
            self.mic_button.setEnabled(True)
            self.append_log(
                "Wake-word microphone is still active. "
                "Voice capture cancelled."
            )
            return

        self.mic_button.setEnabled(False)
        self.mic_button.setText("Listening…")
        self.view.set_listening(True)
        self.append_log("🎙 Listening for one utterance. Speak now...")

        self.submit_wake_transcript = from_wake_word
        self.voice_input_worker = VoiceInputWorker(self.kernel)
        self.voice_input_worker.transcript_signal.connect(self.on_voice_transcript)
        self.voice_input_worker.error_signal.connect(self.on_voice_error)
        self.voice_input_worker.finished.connect(self.on_voice_input_finished)
        self.voice_input_worker.start()

    def on_voice_transcript(self, text: str, confidence: float | None):
        """Send wake-word requests and let users review manual dictation."""
        # Reject empty or non-speech Whisper output.
        cleaned = text.strip()
        if not is_valid_speech_transcript(cleaned):
            self.append_log(
                "No valid speech detected. Ignoring transcript."
            )
            self.submit_wake_transcript = False
            self.voice_conversation = False
            return

        if confidence is None:
            self.append_log("Whisper transcribed the utterance.")
        else:
            self.append_log(f"Speech recognized (confidence {confidence:.2f}).")
        self.view.show_page("Assistant")
        if self.submit_wake_transcript and self.msg_input.text().strip():
            self.append_log(f"Voice request: {text}")
            self.append_log("Finish the current draft before sending another request.")
            return
        self.msg_input.setText(text)
        if self.submit_wake_transcript and (
            self.worker is None or not self.worker.isRunning()
        ):
            self.send_message(from_wake_word=True)
            return
        self.msg_input.setFocus()
        self.msg_input.setCursorPosition(len(text))
        self.append_log("Review or correct the transcript, then press Send.")

    def on_voice_error(self, message: str):
        self.voice_conversation = False
        self.append_log(f"Voice input error: {message}")
        self.view.set_activity("Voice input", message)

    def on_voice_input_finished(self):
        self.submit_wake_transcript = False
        self.mic_button.setEnabled(True)
        self.mic_button.setText("Listen")
        self.view.set_listening(False)
        if not self.voice_conversation:
            self.end_voice_conversation()

    def end_voice_conversation(self):
        self.voice_conversation = False
        if self.closing:
            return
        if self.resume_wake_word:
            self.resume_wake_word = False
            self.arm_wake_word()

    def toggle_voice_output(self):
        """Enable or disable automatic spoken AI responses."""
        self.voice_output_enabled = not self.voice_output_enabled
        self.voice_output_button.setText(
            "Voice: ON" if self.voice_output_enabled else "Voice: OFF"
        )
        if not self.voice_output_enabled:
            self._pending_speech = None
            self.end_voice_conversation()
            self.kernel.voice_service.stop_speaking()
            self.append_log("Spoken responses disabled.")
        else:
            self.append_log("Spoken responses enabled.")

    def start_speech_output(self, text: str):
        """Speak a response without blocking the Qt event loop or triggering wake word."""
        if self.closing or not self.kernel.is_running():
            self.append_log("Speech output skipped because ORB is not running.")
            return

        previous = self.speech_output_worker
        if previous is not None and previous.isRunning():
            self._pending_speech = text
            self.kernel.voice_service.stop_speaking()
            return

        if self.kernel.voice_service.is_wake_word_active:
            # Pause wake-word listening so ORB's own speech cannot self-activate.
            self.resume_wake_word = True
            self._pending_speech = text
            if self.wake_handoff_worker is None or not self.wake_handoff_worker.isRunning():
                self.wake_handoff_worker = WakeWordHandoffWorker(self.kernel)
                self.wake_handoff_worker.ready.connect(self._launch_pending_speech)
                self.wake_handoff_worker.error_signal.connect(self.on_speech_output_error)
                self.wake_handoff_worker.start()
            return

        self._begin_speech_output(text)

    def _launch_pending_speech(self):
        text = self._pending_speech
        self._pending_speech = None
        if text and not self.closing and self.voice_output_enabled:
            self._begin_speech_output(text)
        elif not self.closing:
            self.end_voice_conversation()

    def _begin_speech_output(self, text: str):
        if self.closing or not self.kernel.is_running():
            return
        self.speech_output_worker = SpeechOutputWorker(self.kernel, text)
        self.speech_output_worker.error_signal.connect(
            self.on_speech_output_error
        )
        self.speech_output_worker.finished.connect(self.on_speech_output_finished)
        self.speech_output_worker.start()

    def on_speech_output_error(self, message):
        self._pending_speech = None
        self.append_log(f"Speech output error: {message}")
        self.end_voice_conversation()

    def on_speech_output_finished(self):
        if self._pending_speech and not self.closing and self.voice_output_enabled:
            self._launch_pending_speech()
            return
        if (
            self.voice_conversation and self.voice_output_enabled
            and not self.closing and not self.msg_input.text().strip()
        ):
            self.start_wake_voice_input()
        else:
            self.end_voice_conversation()

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.view.set_activity("Working", "Finish the current request before closing ORB.")
            event.ignore()
            return
        self.closing = True
        self._pending_speech = None
        try:
            kernel = getattr(self, "kernel", None)
            if kernel is not None and kernel.is_running():
                kernel.voice_service.stop_speaking()
                kernel.voice_service.disable_wake_word()

            # Do not destroy a running QThread. One-shot capture is bounded by
            # the configured recording and recognizer timeouts.
            for worker in (
                self.wake_handoff_worker,
                self.voice_input_worker,
                self.speech_output_worker,
            ):
                if worker is not None and worker.isRunning():
                    worker.wait()

            if kernel is not None:
                kernel.stop()
        except Exception as error:
            print(f"ORB shutdown warning: {error}")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ORBLLMDashboard()
    window.show()
    sys.exit(app.exec())
