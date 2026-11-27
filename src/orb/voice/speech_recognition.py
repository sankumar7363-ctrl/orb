"""Local speech recognition adapters for ORB.

The primary engine is Whisper through ONNX Runtime (onnx-asr). The Windows
System.Speech implementation remains available as an explicit fallback.
Microphone access occurs only inside ``listen_once``.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from math import gcd

_NON_SPEECH_MARKER_RE = re.compile(r"\[[^\]]*\]|\([^)]*\)|\*[^*]*\*")


def is_valid_speech_transcript(text: str) -> bool:
    """Return True if *text* contains actual spoken content rather than Whisper markers or silence."""
    if not isinstance(text, str):
        return False
    without_markers = _NON_SPEECH_MARKER_RE.sub(" ", text).strip()
    return any(ch.isalnum() for ch in without_markers)


@dataclass(frozen=True, slots=True)
class RecognitionResult:
    """A speech transcript and optional engine-provided confidence.

    Whisper's standard text adapter does not provide a calibrated confidence
    score, so ``confidence`` is None for Whisper results. Do not synthesize a
    confidence value from text length or other heuristics.
    """

    text: str
    confidence: float | None = None


class WhisperOnnxRecognizer:
    """Lazy-loaded Whisper recognizer backed by ONNX Runtime."""

    def __init__(self, language: str = "en-US", model_name: str = "whisper-base") -> None:
        self.language = language.split("-", 1)[0].strip().lower() or "en"
        self.model_name = model_name
        self._model = None
        self._lock = threading.RLock()

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            import onnx_asr
        except ImportError as error:
            raise RuntimeError(
                "ONNX-ASR is not installed. Install ORB with `py -m pip install -e \".[voice]\"`."
            ) from error

        # Loading is intentionally lazy: kernel startup does not load the
        # model, allocate its runtime memory, or trigger a network download.
        self._model = onnx_asr.load_model(self.model_name)
        return self._model

    def recognize_file(self, wav_path: str | Path) -> RecognitionResult:
        """Transcribe a mono 16 kHz PCM WAV file in the configured language."""
        audio_path = Path(wav_path).expanduser().resolve()
        if not audio_path.is_file():
            raise FileNotFoundError(f"Speech input WAV does not exist: {audio_path}")

        with self._lock:
            model = self._load_model()
            text = model.recognize(str(audio_path), language=self.language)

        if not isinstance(text, str):
            raise RuntimeError(
                "Whisper returned an unexpected result type: "
                f"{type(text).__name__}. Expected a transcript string."
            )
        return RecognitionResult(text=text.strip(), confidence=None)

    def shutdown(self) -> None:
        """Release the cached model reference; it will reload on next use."""
        with self._lock:
            self._model = None


class WindowsSpeechRecognizer:
    """Transcribe a WAV file with the locally installed System.Speech engine."""

    _POWERSHELL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$engine = $null
try {
    Add-Type -AssemblyName System.Speech
    $culture = [System.Globalization.CultureInfo]::GetCultureInfo($env:ORB_STT_LANGUAGE)
    $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($culture)
    $grammar = New-Object System.Speech.Recognition.DictationGrammar
    $engine.LoadGrammar($grammar)
    $engine.SetInputToWaveFile($env:ORB_STT_AUDIO_PATH)
    $result = $engine.Recognize([TimeSpan]::FromSeconds([double]$env:ORB_STT_TIMEOUT))
    if ($null -eq $result) {
        [PSCustomObject]@{ text = ''; confidence = 0.0 } | ConvertTo-Json -Compress
    }
    else {
        [PSCustomObject]@{
            text = [string]$result.Text
            confidence = [double]$result.Confidence
        } | ConvertTo-Json -Compress
    }
}
catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 2
}
finally {
    if ($null -ne $engine) { $engine.Dispose() }
}
"""

    def __init__(self, language: str = "en-US", timeout_seconds: float = 10.0) -> None:
        self.language = language
        self.timeout_seconds = timeout_seconds

    def recognize_file(self, wav_path: str | Path) -> RecognitionResult:
        """Recognize speech in a mono 16 kHz PCM WAV file."""
        if sys.platform != "win32":
            raise RuntimeError("Windows System.Speech recognition is available only on Windows.")

        audio_path = Path(wav_path).expanduser().resolve()
        if not audio_path.is_file():
            raise FileNotFoundError(f"Speech input WAV does not exist: {audio_path}")

        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if not powershell:
            raise RuntimeError("Windows PowerShell was not found; System.Speech cannot be started.")

        encoded_script = base64.b64encode(
            self._POWERSHELL_SCRIPT.encode("utf-16le")
        ).decode("ascii")
        environment = os.environ.copy()
        environment.update(
            {
                "ORB_STT_AUDIO_PATH": str(audio_path),
                "ORB_STT_LANGUAGE": self.language,
                "ORB_STT_TIMEOUT": str(self.timeout_seconds),
            }
        )

        try:
            completed = subprocess.run(
                [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_script],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
                timeout=self.timeout_seconds + 15.0,
            )
        except subprocess.TimeoutExpired as error:
            raise TimeoutError("Windows speech recognition timed out.") from error

        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"Windows speech recognition failed: {detail}")

        try:
            payload = json.loads(completed.stdout.strip())
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"Windows speech recognizer returned unexpected output: {completed.stdout!r}"
            ) from error

        return RecognitionResult(
            text=str(payload.get("text", "")).strip(),
            confidence=float(payload.get("confidence", 0.0)),
        )


class SpeechRecognitionAdapter:
    """Capture one microphone utterance and transcribe it locally."""

    def __init__(
        self,
        *,
        language: str = "en-US",
        microphone_device: int | None = None,
        record_seconds: float = 8.0,
        recognition_timeout: float = 10.0,
        engine: str = "onnx-whisper",
        model_name: str = "whisper-base",
    ) -> None:
        if record_seconds <= 0:
            raise ValueError("record_seconds must be greater than zero.")
        if recognition_timeout <= 0:
            raise ValueError("recognition_timeout must be greater than zero.")

        self.microphone_device = microphone_device
        self.record_seconds = record_seconds
        self.engine_name = engine.strip().lower()

        if self.engine_name == "onnx-whisper":
            self.recognizer = WhisperOnnxRecognizer(language, model_name)
        elif self.engine_name == "windows-system-speech":
            self.recognizer = WindowsSpeechRecognizer(language, recognition_timeout)
        else:
            raise ValueError(
                "Unsupported STT engine. Choose 'onnx-whisper' or 'windows-system-speech'."
            )

    def listen_once(self, duration_seconds: float | None = None) -> RecognitionResult:
        """Record one utterance, resample to 16 kHz mono PCM, and transcribe."""
        try:
            import numpy as np
            import sounddevice as sd
            import soundfile as sf
            from scipy.signal import resample_poly
        except ImportError as error:
            raise RuntimeError(
                "Voice audio dependencies are missing. Install ORB with the [voice] extra."
            ) from error

        duration = float(duration_seconds if duration_seconds is not None else self.record_seconds)
        if duration <= 0:
            raise ValueError("duration_seconds must be greater than zero.")

        device = self.microphone_device
        if device is None:
            default_input = sd.default.device[0]
            device = None if default_input is None or int(default_input) < 0 else int(default_input)

        device_info = sd.query_devices(device, "input")
        input_rate = int(device_info["default_samplerate"])
        samples = sd.rec(
            int(round(duration * input_rate)),
            samplerate=input_rate,
            channels=1,
            dtype="float32",
            device=device,
        )
        sd.wait()
        samples = np.asarray(samples, dtype=np.float32).reshape(-1)

        if samples.size == 0:
            raise RuntimeError("The microphone returned an empty recording.")
        peak = float(np.max(np.abs(samples)))
        if peak < 0.0001:
            raise RuntimeError(
                "No microphone signal was captured. Check the selected input device and microphone level."
            )

        # Apply only a bounded gain similar to the successful manual test.
        # Avoid forcing every recording to full scale, which amplifies noise.
        gain = min(0.5 / peak, 4.0)
        samples = np.clip(samples * gain, -1.0, 1.0)

        target_rate = 16000
        if input_rate != target_rate:
            divisor = gcd(input_rate, target_rate)
            samples = resample_poly(
                samples,
                target_rate // divisor,
                input_rate // divisor,
            ).astype(np.float32)

        with tempfile.TemporaryDirectory(prefix="orb-stt-") as temp_dir:
            wav_path = Path(temp_dir) / "utterance.wav"
            sf.write(str(wav_path), samples, target_rate, subtype="PCM_16")
            return self.recognizer.recognize_file(wav_path)

    def shutdown(self) -> None:
        """Release resources held by the selected recognizer, if supported."""
        shutdown = getattr(self.recognizer, "shutdown", None)
        if callable(shutdown):
            shutdown()
