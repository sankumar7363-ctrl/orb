"""Custom OpenWakeWord listener for ORB."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable


class OpenWakeWordDetector:
    """Listen for a user-trained ORB ONNX wake-word model."""

    def __init__(
        self,
        model_path: str | Path,
        *,
        threshold: float = 0.5,
        microphone_device: int | None = None,
        cooldown_seconds: float = 2.0,
    ) -> None:
        if not 0.0 < threshold <= 1.0:
            raise ValueError("Wake-word threshold must be in the range (0, 1].")
        self.model_path = Path(model_path).expanduser()
        self.threshold = threshold
        self.microphone_device = microphone_device
        self.cooldown_seconds = cooldown_seconds
        self._model = None

    def listen(
        self,
        stop_event: threading.Event,
        on_detected: Callable[[float], None],
        on_ready: Callable[[], None] | None = None,
    ) -> None:
        """Block until stopped, calling ``on_detected`` when the phrase is heard."""
        if not self.model_path.is_file():
            raise FileNotFoundError(
                "The custom 'Hey ORB' model is not installed yet: "
                f"{self.model_path}. Train/export hey_orb.onnx before enabling wake-word listening."
            )

        try:
            import numpy as np
            import sounddevice as sd
            from scipy.signal import resample_poly
            from openwakeword.model import Model
        except ImportError as error:
            raise RuntimeError("OpenWakeWord or its audio dependencies are not installed.") from error

        if self._model is None:
            self._model = Model(
                wakeword_models=[str(self.model_path)],
                inference_framework="onnx",
            )
        model = self._model
        model.reset()
        if stop_event.is_set():
            return
        device = self.microphone_device
        if device is None:
            default_input = sd.default.device[0]
            device = None if default_input is None or int(default_input) < 0 else int(default_input)
        device_info = sd.query_devices(device, "input")
        input_rate = int(device_info["default_samplerate"])
        input_block = int(round(input_rate * 0.08))  # OpenWakeWord's 80 ms frame.
        last_detection = 0.0
        consecutive_hits = 0
        warmup_frames = 20

        with sd.InputStream(
            device=device,
            samplerate=input_rate,
            channels=1,
            dtype="int16",
            blocksize=input_block,
        ) as stream:
            while not stop_event.is_set():
                audio, overflowed = stream.read(input_block)
                if overflowed:
                    # A single missed frame should not kill the listener.
                    consecutive_hits = 0
                    continue
                frame = np.asarray(audio, dtype=np.int16).reshape(-1)
                if input_rate != 16000:
                    from math import gcd

                    divisor = gcd(input_rate, 16000)
                    converted = resample_poly(
                        frame.astype(np.float32),
                        16000 // divisor,
                        input_rate // divisor,
                    )
                    frame = np.clip(converted, -32768, 32767).astype(np.int16)
                if frame.size < 1280:
                    continue
                for offset in range(0, frame.size - 1279, 1280):
                    chunk = frame[offset : offset + 1280]
                    scores = model.predict(chunk)
                    # Fill the model's audio history before accepting detections.
                    # Partial startup history can produce high scores on room noise.
                    if warmup_frames:
                        warmup_frames -= 1
                        if warmup_frames == 0 and on_ready is not None and not stop_event.is_set():
                            on_ready()
                        continue
                    score = max((float(value) for value in scores.values()), default=0.0)
                    # Reject isolated score spikes and silent frames.
                    if score < self.threshold or not chunk.any():
                        consecutive_hits = 0
                        continue
                    consecutive_hits += 1
                    now = time.monotonic()
                    if consecutive_hits >= 2 and now - last_detection >= self.cooldown_seconds:
                        last_detection = now
                        consecutive_hits = 0
                        on_detected(score)
                        break
