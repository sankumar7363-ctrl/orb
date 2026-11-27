import unittest
from unittest.mock import patch

from orb.voice.service import VoiceService
from orb.voice.wake_word import OpenWakeWordDetector


class VoiceServiceTests(unittest.TestCase):
    def test_lifecycle_starts_without_opening_microphone(self):
        service = VoiceService()
        service.configure({})
        service.initialize()
        service.start()

        self.assertTrue(service.is_started)
        self.assertFalse(service.is_wake_word_active)

        service.stop()
        service.shutdown()
        self.assertFalse(service.is_started)

    def test_wake_word_is_disabled_by_default(self):
        service = VoiceService()
        service.configure({})
        service.initialize()
        service.start()

        with self.assertRaisesRegex(RuntimeError, "disabled"):
            service.enable_wake_word(lambda score: None)

        service.shutdown()

    def test_custom_wake_word_requires_existing_model_when_enabled(self):
        service = VoiceService()
        service.configure(
            {
                "voice": {
                    "wake_word": {
                        "enabled": True,
                        "model_path": "E:/ORB/Models/Voices/hey_orb.onnx",
                    }
                }
            }
        )
        service.initialize()
        service.start()

        with patch.object(service._wake_detector, "listen", side_effect=FileNotFoundError("missing model")):
            service.enable_wake_word(lambda score: None)
            service._wake_thread.join(timeout=2)

        self.assertFalse(service.is_wake_word_active)
        service.shutdown()

    def test_listen_requires_started_service(self):
        service = VoiceService()
        service.configure({})
        with self.assertRaisesRegex(RuntimeError, "not started"):
            service.listen_once()
        service.shutdown()

    def test_listen_once_rejected_while_wake_word_is_active(self):
        from threading import Event

        service = VoiceService()
        service.configure({"voice": {"wake_word": {"enabled": True}}})
        service.initialize()
        service.start()

        started = Event()

        def blocking_listen(stop_event, _on_detected, _on_ready=None):
            started.set()
            stop_event.wait(timeout=2.0)

        with patch.object(service._wake_detector, "listen", side_effect=blocking_listen):
            service.enable_wake_word(lambda _score: None)
            self.assertTrue(started.wait(timeout=1.0))
            with self.assertRaisesRegex(RuntimeError, "Wake-word listener"):
                service.listen_once()
            service.disable_wake_word()

        service.shutdown()

    def test_restart_cycle_preserves_service_usability(self):
        service = VoiceService()
        service.configure({})
        service.initialize()
        service.start()
        service.stop()
        self.assertFalse(service.is_started)
        service.start()
        self.assertTrue(service.is_started)
        service.shutdown()


def test_wake_listener_ignores_startup_and_isolated_scores(tmp_path):
    from threading import Event
    from unittest.mock import Mock

    import pytest

    np = pytest.importorskip("numpy")
    sd = pytest.importorskip("sounddevice")
    pytest.importorskip("scipy.signal")
    pytest.importorskip("openwakeword.model")

    model_path = tmp_path / "orb.onnx"
    model_path.touch()
    detector = OpenWakeWordDetector(model_path, microphone_device=1, cooldown_seconds=0)
    model = Mock()
    detector._model = model
    model.predict.side_effect = [
        {"orb": score} for score in [0.9] * 20 + [0.8, 0.1, 0.8, 0.9]
    ]
    audio_stream = Mock()
    audio_stream.read.return_value = np.ones((1280, 1), dtype=np.int16), False
    audio_context = Mock()
    audio_context.__enter__ = Mock(return_value=audio_stream)
    audio_context.__exit__ = Mock(return_value=False)
    stop = Event()
    ready_at = []
    detections = []

    def on_detected(score):
        detections.append((model.predict.call_count, score))
        stop.set()

    with (
        patch.object(sd, "query_devices", return_value={"default_samplerate": 16000}),
        patch.object(sd, "InputStream", return_value=audio_context),
    ):
        detector.listen(stop, on_detected, lambda: ready_at.append(model.predict.call_count))

    assert ready_at == [20]
    assert detections == [(24, 0.9)]


if __name__ == "__main__":
    unittest.main()
