"""Discover, validate, load, and manage external ORB plugins."""

from __future__ import annotations

import importlib.util
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from orb.core.constants import PROJECT_ROOT
from orb.logging import get_logger


class Plugin(Protocol):
    """Lifecycle contract for a plugin loaded by ORB."""

    name: str

    def initialize(self) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def shutdown(self) -> None: ...


class PluginError(RuntimeError):
    """Raised when plugin discovery, loading, or validation fails."""


class PluginManager:
    """Load plugins from Python modules and manage their lifecycle."""

    def __init__(self, directories: Iterable[Path | str] | None = None) -> None:
        self._directories = tuple(Path(directory) for directory in directories) if directories else (PROJECT_ROOT / "plugins",)
        self._plugins: dict[str, Plugin] = {}
        self._initialized: list[str] = []
        self._started: list[str] = []
        self._logger = get_logger("plugins")

    @property
    def plugin_names(self) -> tuple[str, ...]:
        """Return plugin names in load order."""
        return tuple(self._plugins)

    def discover(self) -> tuple[Path, ...]:
        """Return loadable plugin modules from configured directories."""
        discovered: list[Path] = []
        for directory in self._directories:
            if not directory.exists():
                continue
            if not directory.is_dir():
                raise PluginError(f"Plugin path is not a directory: {directory}")
            discovered.extend(path for path in sorted(directory.glob("*.py")) if not path.name.startswith("_"))
        return tuple(discovered)

    def load_all(self) -> tuple[str, ...]:
        """Discover and load every configured plugin module."""
        for path in self.discover():
            self.load(path)
        return self.plugin_names

    def load(self, path: Path | str) -> Plugin:
        """Load one plugin module and return its validated plugin object."""
        module_path = Path(path)
        if not module_path.is_file() or module_path.suffix != ".py":
            raise PluginError(f"Plugin module does not exist: {module_path}")
        module_name = f"orb_external_plugin_{module_path.stem}_{abs(hash(module_path.resolve()))}"
        specification = importlib.util.spec_from_file_location(module_name, module_path)
        if specification is None or specification.loader is None:
            raise PluginError(f"Unable to create plugin specification: {module_path}")
        module = importlib.util.module_from_spec(specification)
        try:
            specification.loader.exec_module(module)
        except Exception as error:
            raise PluginError(f"Unable to load plugin module {module_path}: {error}") from error
        plugin = getattr(module, "PLUGIN", None)
        if plugin is None and callable(factory := getattr(module, "create_plugin", None)):
            plugin = factory()
        self._validate_plugin(plugin, module_path)
        if plugin.name in self._plugins:
            raise PluginError(f"Plugin is already loaded: {plugin.name}")
        self._plugins[plugin.name] = plugin
        self._logger.info("Loaded plugin '%s'", plugin.name)
        return plugin

    def initialize(self) -> None:
        """Initialize all loaded plugins."""
        for name, plugin in self._plugins.items():
            if name not in self._initialized:
                plugin.initialize()
                self._initialized.append(name)

    def start(self) -> None:
        """Start all loaded plugins after initialization."""
        self.initialize()
        for name, plugin in self._plugins.items():
            if name not in self._started:
                plugin.start()
                self._started.append(name)

    def shutdown(self) -> None:
        """Stop and shutdown plugins in reverse load order."""
        for name in reversed(self._started):
            self._plugins[name].stop()
        self._started.clear()
        for name in reversed(self._initialized):
            self._plugins[name].shutdown()
        self._initialized.clear()

    @staticmethod
    def _validate_plugin(plugin: object, path: Path) -> None:
        if not isinstance(getattr(plugin, "name", None), str) or not plugin.name.strip():
            raise PluginError(f"Plugin in {path} must have a non-empty name.")
        methods = ("initialize", "start", "stop", "shutdown")
        missing = [method for method in methods if not callable(getattr(plugin, method, None))]
        if missing:
            raise PluginError(f"Plugin in {path} is missing lifecycle methods: {', '.join(missing)}")
