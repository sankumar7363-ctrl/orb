"""Lifecycle-managed ORB voice service."""

from __future__ import annotations

import logging
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Callable

from orb.voice.speech_recognition import RecognitionResult, SpeechRecognitionAdapter
from orb.voice.speech_synthesis import PiperSpeechSynthesizer
from orb.voice.wake_word import OpenWakeWordDetector


class VoiceService:
    """Coordinate local STT, TTS, and optional Hey ORB wake-word detection.

    The service never opens the microphone during initialize() or start().
    Microphone capture occurs only after an explicit listen_once() call or
    enable_wake_word() call from the application/UI.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger("orb.voice")
        self._started = False
        self._initialized = False
        self._settings: dict[str, object] = {}
        self._recognizer: SpeechRecognitionAdapter | None = None
        self._synthesizer: PiperSpeechSynthesizer | None = None
        self._wake_detector: OpenWakeWordDetector | None = None
        self._wake_stop = threading.Event()
        self._wake_thread: threading.Thread | None = None
        self._capture_active = False
        self._lock = threading.RLock()

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def minimum_confidence(self) -> float:
        """Return the minimum acceptable speech-recognition confidence."""
        return float(self._settings.get("minimum_confidence", 0.60))

    @property
    def is_wake_word_active(self) -> bool:
        return self._wake_thread is not None and self._wake_thread.is_alive()

    def configure(self, application_config: Mapping[str, object]) -> None:
        """Read the optional ``[voice]`` section from ORB configuration."""
        voice = application_config.get("voice", {})
        if not isinstance(voice, Mapping):
            raise TypeError("The [voice] configuration section must be a table.")
        synthesis = voice.get("synthesis", {})
        wake_word = voice.get("wake_word", {})
        if not isinstance(synthesis, Mapping) or not isinstance(wake_word, Mapping):
            raise TypeError("[voice.synthesis] and [voice.wake_word] must be tables.")

        self._settings = {
            "language": str(voice.get("language", "en-US")),
            "record_seconds": float(voice.get("record_seconds", 8.0)),
            "minimum_confidence": float(voice.get("minimum_confidence", 0.60)),
            "stt_engine": str(voice.get("stt_engine", "onnx-whisper")),
            "stt_model": str(voice.get("stt_model", "whisper-base")),
            "microphone_device": voice.get("microphone_device", None),
            "playback_device": voice.get("playback_device", None),
            "piper_model_path": str(
                synthesis.get("model_path", "E:/ORB/Models/Voices/en_US-ryan-medium.onnx")
            ),
            "wake_word_enabled": bool(wake_word.get("enabled", False)),
            "wake_word_model_path": str(
                wake_word.get("model_path", "E:/ORB/Models/Voices/hey_orb.onnx")
            ),
            "wake_word_threshold": float(wake_word.get("threshold", 0.5)),
        }
        self._recognizer = None
        self._synthesizer = None
        self._wake_detector = None

    def initialize(self) -> None:
        """Prepare lightweight adapters without loading models or opening audio."""
        if not self._settings:
            self.configure({})
        self._recognizer = SpeechRecognitionAdapter(
            language=str(self._settings["language"]),
            microphone_device=self._optional_int(self._settings["microphone_device"]),
            record_seconds=float(self._settings["record_seconds"]),
            engine=str(self._settings["stt_engine"]),
            model_name=str(self._settings["stt_model"]),
        )
        self._synthesizer = PiperSpeechSynthesizer(
            str(self._settings["piper_model_path"]),
            playback_device=self._optional_int(self._settings["playback_device"]),
        )
        self._wake_detector = OpenWakeWordDetector(
            str(self._settings["wake_word_model_path"]),
            threshold=float(self._settings["wake_word_threshold"]),
            microphone_device=self._optional_int(self._settings["microphone_device"]),
        )
        self._initialized = True
        self._logger.info("Voice service initialized; microphone remains inactive")

    def start(self) -> None:
        """Mark the service available; do not activate the microphone."""
        if not self._initialized:
            self.initialize()
        self._started = True
        self._logger.info("Voice service started; voice activation is opt-in")

    def listen_once(self, duration_seconds: float | None = None) -> RecognitionResult:
        """Capture and transcribe one utterance using the configured recognizer."""
        with self._lock:
            self._ensure_started()
            if self.is_wake_word_active:
                raise RuntimeError(
                    "Wake-word listener is currently using the microphone. Disable wake-word listening first."
                )
            if self._capture_active:
                raise RuntimeError("Microphone capture is already in progress.")
            self._capture_active = True
            recognizer = self._recognizer
        assert recognizer is not None
        try:
            return recognizer.listen_once(duration_seconds)
        finally:
            with self._lock:
                self._capture_active = False

    def speak(self, text: str) -> None:
        """Speak text locally with the configured Piper voice."""
        self._ensure_started()
        assert self._synthesizer is not None
        self._synthesizer.speak(text)

    def stop_speaking(self) -> None:
        """Stop current TTS playback without stopping the voice service."""
        if self._synthesizer is not None:
            self._synthesizer.stop()

    def enable_wake_word(
        self,
        on_detected: Callable[[float], None],
        *,
        on_ready: Callable[[], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        """Start the custom wake-word listener after explicit enablement."""
        with self._lock:
            self._ensure_started()
            if not bool(self._settings.get("wake_word_enabled", False)):
                raise RuntimeError(
                    "Wake-word activation is disabled in configs/orb.toml. "
                    "Enable [voice.wake_word].enabled only after installing the Hey ORB model."
                )
            if self._capture_active:
                raise RuntimeError("Microphone capture is currently in progress.")
            if self.is_wake_word_active:
                return
            if not callable(on_detected):
                raise TypeError("on_detected must be callable.")
            if self._wake_detector is None:
                raise RuntimeError("Wake-word detector has not been initialized.")

            self._wake_stop.clear()

            def listener_ready() -> None:
                self._logger.info("ORB wake-word microphone ready")
                if on_ready is not None:
                    on_ready()

            def run_listener() -> None:
                try:
                    assert self._wake_detector is not None
                    self._wake_detector.listen(self._wake_stop, on_detected, listener_ready)
                except Exception as error:
                    self._logger.exception("Wake-word listener stopped unexpectedly")
                    if on_error is not None and not self._wake_stop.is_set():
                        on_error(str(error))

            self._wake_thread = threading.Thread(
                target=run_listener,
                name="orb-wake-word",
                daemon=True,
            )
            self._wake_thread.start()
            self._logger.info("ORB wake-word listener starting")

    def disable_wake_word(self) -> None:
        """Stop the wake-word listener and release its microphone stream."""
        with self._lock:
            self._wake_stop.set()
            thread = self._wake_thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=5.0)
        with self._lock:
            if thread is not None and thread.is_alive():
                self._logger.warning("Wake-word listener has not released the microphone yet")
            else:
                self._wake_thread = None
                self._logger.info("Wake-word listener stopped")

    def stop(self) -> None:
        """Stop active audio work without unloading reusable adapters."""
        self.disable_wake_word()
        if self._synthesizer is not None:
            self._synthesizer.stop()
        self._started = False

    def shutdown(self) -> None:
        """Release cached model references and service state."""
        self.stop()
        if self._recognizer is not None:
            self._recognizer.shutdown()
        if self._synthesizer is not None:
            self._synthesizer.shutdown()
        self._recognizer = None
        self._synthesizer = None
        self._wake_detector = None
        self._initialized = False

    def _ensure_started(self) -> None:
        if not self._started:
            raise RuntimeError("VoiceService is not started. Start the ORB kernel first.")

    @staticmethod
    def _optional_int(value: object) -> int | None:
        if value is None or value == "":
            return None
        return int(value)
