"""Configure consistent console and file logging for ORB."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orb.core.constants import DEFAULT_LOG_LEVEL, LOG_DIRECTORY

LOGGER_NAME = "orb"
DEFAULT_LOG_FILE = "orb.log"


class JsonFormatter(logging.Formatter):
    """Render log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        """Format *record* while preserving useful exception information."""
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(configuration: Mapping[str, Any] | None = None) -> logging.Logger:
    """Configure and return ORB's root logger.

    ``configuration`` may contain a ``logging`` table with ``level``,
    ``directory``, and ``file_name`` fields.  Reconfiguration replaces only
    handlers managed by this module, making repeated application starts safe.
    """
    settings = _logging_settings(configuration)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(_level(settings["level"]))
    logger.propagate = False
    _remove_managed_handlers(logger)

    formatter = JsonFormatter()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    directory = Path(settings["directory"])
    directory.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(directory / settings["file_name"], encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return an ORB logger, optionally scoped to a component name."""
    if not name:
        return logging.getLogger(LOGGER_NAME)
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def shutdown_logging() -> None:
    """Close all handlers managed by ORB.

    This releases the log file promptly on Windows during application shutdown.
    """
    _remove_managed_handlers(logging.getLogger(LOGGER_NAME))


def _logging_settings(configuration: Mapping[str, Any] | None) -> dict[str, str]:
    logging_config = configuration.get("logging", {}) if configuration else {}
    if not isinstance(logging_config, Mapping):
        logging_config = {}
    return {
        "level": str(logging_config.get("level", DEFAULT_LOG_LEVEL)),
        "directory": str(logging_config.get("directory", LOG_DIRECTORY)),
        "file_name": str(logging_config.get("file_name", DEFAULT_LOG_FILE)),
    }


def _level(value: str) -> int:
    level = logging.getLevelName(value.upper())
    if not isinstance(level, int):
        raise ValueError(f"Invalid ORB log level: {value}")
    return level


def _remove_managed_handlers(logger: logging.Logger) -> None:
    """Remove and close handlers attached directly to the ORB root logger."""
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
