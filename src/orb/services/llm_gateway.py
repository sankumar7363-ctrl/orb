"""
=============================================================
ORB Platform
Unified LLM Gateway (Plug-and-Play Provider)

Author: Santosh Kumar
=============================================================
"""

import json
import requests
from pathlib import Path
from orb.logging import get_logger

logger = get_logger("service.llm_gateway")

class LLMGateway:
    """Manages active LLM provider dynamically based on configuration."""

    def __init__(self, config_path: str = "Platform/orb/config.json"):
        self.config = self._load_config(config_path)
        active_key = self.config.get("active_llm_provider", "ollama")
        self.provider_config = self.config.get("providers", {}).get(active_key, {})

        self.model_name = self.provider_config.get("model_name", "llama3")
        self.url = self.provider_config.get("url", "http://localhost:11434/api/generate")

        logger.info("LLM Gateway initialized with provider '%s' (Model: %s)", active_key, self.model_name)

    def _load_config(self, path: str) -> dict:
        try:
            config_file = Path(path)
            if config_file.exists():
                with open(config_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning("Could not load config file (%s). Using defaults.", e)

        return {
            "active_llm_provider": "ollama",
            "providers": {
                "ollama": {
                    "model_name": "llama3",
                    "url": "http://localhost:11434/api/generate"
                }
            }
        }

    def generate(self, prompt: str) -> str:
        """Unified method to call whichever LLM is currently active."""
        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception as e:
            logger.error("LLM Gateway generation failed: %s", e)

        return ""
