"""Local Piper text-to-speech adapter."""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path


class PiperSpeechSynthesizer:
    """Synthesize speech locally with a cached Piper voice model."""

    def __init__(self, model_path: str | Path, playback_device: int | None = None) -> None:
        self.model_path = Path(model_path).expanduser()
        self.playback_device = playback_device
        self._voice = None
        self._lock = threading.RLock()

    def _load_voice(self):
        if self._voice is not None:
            return self._voice
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Piper voice model was not found: {self.model_path}")
        try:
            from piper import PiperVoice
        except ImportError as error:
            raise RuntimeError("Piper TTS is not installed. Install ORB with the [voice] extra.") from error
        self._voice = PiperVoice.load(str(self.model_path))
        return self._voice

    def speak(self, text: str) -> None:
        """Generate a temporary WAV and play it through the configured output."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Speech text must be a non-empty string.")
        try:
            import sounddevice as sd
            import soundfile as sf
        except ImportError as error:
            raise RuntimeError("Audio playback dependencies are missing.") from error

        with self._lock:
            voice = self._load_voice()
            with tempfile.TemporaryDirectory(prefix="orb-tts-") as temp_dir:
                wav_path = Path(temp_dir) / "speech.wav"
                import wave

                with wave.open(str(wav_path), "wb") as wav_file:
                    voice.synthesize_wav(text.strip(), wav_file)
                audio, sample_rate = sf.read(str(wav_path), dtype="float32")
                sd.play(audio, int(sample_rate), device=self.playback_device, blocking=True)

    def stop(self) -> None:
        """Stop current playback, if any."""
        try:
            import sounddevice as sd
        except ImportError:
            return
        sd.stop()

    def shutdown(self) -> None:
        """Release the cached voice reference."""
        self.stop()
        with self._lock:
            self._voice = None
