"""Load, validate, and expose ORB configuration."""

from __future__ import annotations

import json
import os
import tomllib
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from orb.core.constants import CONFIG_DIRECTORY, DEFAULT_CONFIG_FILE, DEFAULT_TIMEOUT


class ConfigurationError(ValueError):
    """Raised when ORB configuration cannot be loaded or validated."""


DEFAULT_CONFIGURATION: dict[str, Any] = {
    "application": {
        "name": "ORB",
        "environment": "development",
        "debug": False,
    },
    "runtime": {"default_timeout": DEFAULT_TIMEOUT},
}


@dataclass(frozen=True, slots=True)
class Configuration:
    """An immutable, validated ORB configuration snapshot."""

    values: Mapping[str, Any]
    source: Path | None

    def get(self, key: str, default: Any = None) -> Any:
        """Return a value using a dotted path, or *default* when absent."""
        value: Any = self.values
        for part in key.split("."):
            if not isinstance(value, Mapping) or part not in value:
                return default
            value = value[part]
        return value

    def as_dict(self) -> dict[str, Any]:
        """Return a mutable copy suitable for callers that need one."""
        return _thaw(self.values)


class ConfigurationManager:
    """Build configuration from defaults, an optional TOML file, and the environment.

    Environment overrides use the ``ORB_`` prefix and double underscores for
    nesting.  For example, ``ORB_APPLICATION__DEBUG=true`` overrides
    ``application.debug``.
    """

    ENVIRONMENT_PREFIX = "ORB_"

    def __init__(self, config_path: Path | str | None = None) -> None:
        self._requested_path = Path(config_path) if config_path is not None else None
        self._configuration: Configuration | None = None

    @property
    def configuration(self) -> Configuration:
        """Return the loaded configuration.

        Raises:
            ConfigurationError: If :meth:`load` has not run yet.
        """
        if self._configuration is None:
            raise ConfigurationError("Configuration has not been loaded.")
        return self._configuration

    def load(self) -> Configuration:
        """Load and validate the effective configuration."""
        source = self._resolve_source()
        values = deepcopy(DEFAULT_CONFIGURATION)
        if source is not None:
            values = _deep_merge(values, self._read_toml(source))
        values = _deep_merge(values, self._environment_overrides())
        self._validate(values)
        self._configuration = Configuration(_freeze(values), source)
        return self._configuration

    def _resolve_source(self) -> Path | None:
        candidate = self._requested_path
        if candidate is None and (from_environment := os.getenv("ORB_CONFIG")):
            candidate = Path(from_environment)
        if candidate is None:
            candidate = CONFIG_DIRECTORY / DEFAULT_CONFIG_FILE
        if not candidate.exists():
            if self._requested_path is not None or os.getenv("ORB_CONFIG"):
                raise ConfigurationError(f"Configuration file does not exist: {candidate}")
            return None
        if not candidate.is_file():
            raise ConfigurationError(f"Configuration path is not a file: {candidate}")
        return candidate

    @staticmethod
    def _read_toml(path: Path) -> dict[str, Any]:
        try:
            with path.open("rb") as config_file:
                data = tomllib.load(config_file)
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise ConfigurationError(f"Unable to read configuration file {path}: {error}") from error
        return data

    def _environment_overrides(self) -> dict[str, Any]:
        overrides: dict[str, Any] = {}
        for name, raw_value in os.environ.items():
            if not name.startswith(self.ENVIRONMENT_PREFIX) or name == "ORB_CONFIG":
                continue
            path = name.removeprefix(self.ENVIRONMENT_PREFIX).lower().split("__")
            if any(not segment for segment in path):
                raise ConfigurationError(f"Invalid environment override name: {name}")
            target = overrides
            for segment in path[:-1]:
                target = target.setdefault(segment, {})
            target[path[-1]] = _parse_environment_value(raw_value)
        return overrides

    @staticmethod
    def _validate(values: Mapping[str, Any]) -> None:
        application = values.get("application")
        runtime = values.get("runtime")
        if not isinstance(application, Mapping):
            raise ConfigurationError("application must be a table.")
        if not isinstance(application.get("name"), str) or not application["name"].strip():
            raise ConfigurationError("application.name must be a non-empty string.")
        if not isinstance(application.get("environment"), str) or not application["environment"].strip():
            raise ConfigurationError("application.environment must be a non-empty string.")
        if not isinstance(application.get("debug"), bool):
            raise ConfigurationError("application.debug must be a boolean.")
        if not isinstance(runtime, Mapping):
            raise ConfigurationError("runtime must be a table.")
        timeout = runtime.get("default_timeout")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            raise ConfigurationError("runtime.default_timeout must be a positive integer.")


def _deep_merge(base: dict[str, Any], overrides: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively merge *overrides* into a copy-friendly mapping."""
    for key, value in overrides.items():
        if isinstance(base.get(key), dict) and isinstance(value, Mapping):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = deepcopy(value)
    return base


def _parse_environment_value(value: str) -> Any:
    """Parse JSON-like scalar values while leaving ordinary strings intact."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value

def _thaw(value: Any) -> Any:
    """Convert immutable configuration values into mutable Python objects."""
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}

    if isinstance(value, tuple):
        return [_thaw(item) for item in value]

    return value

def _freeze(value: Any) -> Any:
    """Recursively prevent mutation of the published configuration."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value
