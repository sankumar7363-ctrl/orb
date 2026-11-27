from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from orb.voice.speech_recognition import (
    RecognitionResult,
    SpeechRecognitionAdapter,
    WhisperOnnxRecognizer,
    is_valid_speech_transcript,
)


class WhisperOnnxRecognizerTests(unittest.TestCase):
    def test_model_loads_lazily_and_recognizes_english(self):
        fake_model = Mock()
        fake_model.recognize.return_value = "Hello ORB, how are you?"

        with patch("onnx_asr.load_model", return_value=fake_model) as load_model:
            recognizer = WhisperOnnxRecognizer(language="en-US", model_name="whisper-base")
            load_model.assert_not_called()

            with tempfile.NamedTemporaryFile(suffix=".wav") as audio:
                result = recognizer.recognize_file(audio.name)

            load_model.assert_called_once_with("whisper-base")
            fake_model.recognize.assert_called_once_with(
                str(Path(audio.name).resolve()), language="en"
            )
            self.assertEqual(result.text, "Hello ORB, how are you?")
            self.assertIsNone(result.confidence)
            recognizer.shutdown()

    def test_model_is_reused_until_shutdown(self):
        fake_model = Mock()
        fake_model.recognize.return_value = "Test phrase"

        with patch("onnx_asr.load_model", return_value=fake_model) as load_model:
            recognizer = WhisperOnnxRecognizer()
            with tempfile.NamedTemporaryFile(suffix=".wav") as audio:
                recognizer.recognize_file(audio.name)
                recognizer.recognize_file(audio.name)
                self.assertEqual(load_model.call_count, 1)
                recognizer.shutdown()
                recognizer.recognize_file(audio.name)
                self.assertEqual(load_model.call_count, 2)

    def test_windows_language_code_is_reduced_to_primary_language(self):
        recognizer = WhisperOnnxRecognizer(language="en-US")
        self.assertEqual(recognizer.language, "en")

    def test_adapter_uses_whisper_by_default(self):
        adapter = SpeechRecognitionAdapter()
        self.assertIsInstance(adapter.recognizer, WhisperOnnxRecognizer)
        adapter.shutdown()

    def test_non_speech_markers_and_silence_are_rejected(self):
        for marker in (
            "",
            "   ",
            "[BLANK_AUDIO]",
            "[BLANK_AUDIO] [NOISE]",
            "[Music]",
            "(silence)",
            "[inaudible]",
            "*cough*",
            "...",
            "♪ ♪",
        ):
            self.assertFalse(is_valid_speech_transcript(marker), f"Should reject {marker!r}")

        for spoken in ("Open Brave", "What is your name?", "Search the web for Python"):
            self.assertTrue(is_valid_speech_transcript(spoken), f"Should accept {spoken!r}")


if __name__ == "__main__":
    unittest.main()
