
"""
=============================================================
ORB Platform
AI Provider Abstraction Layer (Local LLM / Ollama)

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from orb.logging import get_logger


class AIProviderError(Exception):
    """Raised when local AI inference fails or returns invalid output."""


class LocalOllamaProvider:
    """Interface for running local LLMs through Ollama."""

    def __init__(
        self,
        endpoint: str = "http://localhost:11434",
        default_model: str = "qwen2.5:3b",
        timeout: int = 30,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout
        self._logger = get_logger("ai.ollama")

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        """Generate a text response using Ollama."""
        try:
            return self._call_ollama_generate(
                prompt, system_prompt, model, temperature
            )
        except Exception as error:
            self._logger.error("Ollama generation failed: %s", error)
            raise AIProviderError(
                f"Local AI generation failed: {error}"
            ) from error

    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Generate and parse a JSON response using Ollama."""
        try:
            return self._call_ollama_json(prompt, system_prompt, model)
        except Exception as error:
            self._logger.error("Ollama JSON generation failed: %s", error)
            raise AIProviderError(
                f"Local AI JSON generation failed: {error}"
            ) from error

    def _call_ollama_generate(
        self,
        prompt: str,
        system_prompt: str | None,
        model: str | None,
        temperature: float,
    ) -> str:
        target_model = model or self.default_model
        url = f"{self.endpoint}/api/generate"

        payload: dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }

        if system_prompt:
            payload["system"] = system_prompt

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            result = json.loads(response.read().decode("utf-8"))

        generated_text = result.get("response")

        if not isinstance(generated_text, str) or not generated_text.strip():
            raise ValueError("Ollama returned an empty or invalid response.")

        return generated_text.strip()

    def _call_ollama_json(
        self,
        prompt: str,
        system_prompt: str | None,
        model: str | None,
    ) -> dict[str, Any]:
        target_model = model or self.default_model
        url = f"{self.endpoint}/api/generate"

        json_system_prompt = (
            (system_prompt or "")
            + "\nYou must output ONLY valid JSON."
        ).strip()

        payload: dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "system": json_system_prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1},
        }

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            result = json.loads(response.read().decode("utf-8"))

        generated_json = result.get("response")

        if not isinstance(generated_json, str) or not generated_json.strip():
            raise ValueError("Ollama returned an empty JSON response.")

        parsed = json.loads(generated_json)

        if not isinstance(parsed, dict):
            raise ValueError("Ollama JSON response must be an object.")

        return parsed
