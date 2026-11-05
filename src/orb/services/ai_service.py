
"""
=============================================================
ORB Platform
AI Service

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from typing import Any, Mapping

from orb.ai.provider import LocalOllamaProvider, AIProviderError
from orb.logging import get_logger


class AIService:
    """Manages the AI Provider lifecycle within ORB."""

    def __init__(self) -> None:
        self._logger = get_logger("service.ai")
        self.provider: LocalOllamaProvider | None = None
        self._config: dict[str, Any] = {}

    def configure(self, configuration: Mapping[str, Any]) -> None:
        """Load AI settings from ORB's central configuration."""
        ai_config = configuration.get("ai", {})

        self._config = {
            "provider": ai_config.get("provider", "ollama"),
            "model": ai_config.get("model", "qwen2.5:3b"),
            "endpoint": ai_config.get(
                "endpoint", "http://localhost:11434"
            ),
            "timeout": ai_config.get("timeout", 30),
            "temperature": ai_config.get("temperature", 0.2),
        }

        self._logger.info(
            "AI configuration loaded. Provider: %s, Model: %s",
            self._config["provider"],
            self._config["model"],
        )

    def initialize(self) -> None:
        """Initialize the configured AI provider."""
        self._logger.debug("Initializing AI Service...")

        if self._config.get("provider") != "ollama":
            raise ValueError(
                f"Unsupported AI provider: {self._config.get('provider')}"
            )

        self.provider = LocalOllamaProvider(
            endpoint=self._config["endpoint"],
            default_model=self._config["model"],
            timeout=self._config["timeout"],
        )

    def start(self) -> None:
        self._logger.info("AI Service started. Provider initialized.")

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate a text response using the configured provider."""
        if self.provider is None:
            raise AIProviderError("AI Service is not initialized.")

        return self.provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=self._config.get("temperature", 0.2),
        )

    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Generate a JSON response using the configured provider."""
        if self.provider is None:
            raise AIProviderError("AI Service is not initialized.")

        return self.provider.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
        )

    def stop(self) -> None:
        self._logger.debug("AI Service stopping.")

    def shutdown(self) -> None:
        self.provider = None
        self._logger.debug("AI Service shut down.")
