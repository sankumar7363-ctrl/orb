"""Register and manage lifecycle-aware ORB services."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from orb.logging import get_logger


class Service(Protocol):
    """Lifecycle contract implemented by services managed by ORB."""

    def initialize(self) -> None:
        """Prepare the service before it starts."""

    def start(self) -> None:
        """Start the service."""

    def stop(self) -> None:
        """Stop the service while dependencies remain available."""

    def shutdown(self) -> None:
        """Release all service resources."""


class ServiceRegistrationError(ValueError):
    """Raised when service registration or dependency resolution fails."""


class ServiceManager:
    """Manage registered services in dependency-safe lifecycle order."""

    def __init__(self) -> None:
        self._services: dict[str, Service] = {}
        self._dependencies: dict[str, tuple[str, ...]] = {}
        self._initialized: list[str] = []
        self._started: list[str] = []
        self._logger = get_logger("services")

    @property
    def service_names(self) -> tuple[str, ...]:
        """Return services in registration order."""
        return tuple(self._services)

    def register(self, name: str, service: Service, *, dependencies: Iterable[str] = ()) -> None:
        """Register a unique service and its required service names."""
        self._validate_name(name)
        if name in self._services:
            raise ServiceRegistrationError(f"Service is already registered: {name}")
        self._validate_service(service)
        dependency_names = tuple(dependencies)
        for dependency in dependency_names:
            self._validate_name(dependency)
        if name in dependency_names:
            raise ServiceRegistrationError(f"Service cannot depend on itself: {name}")
        self._services[name] = service
        self._dependencies[name] = dependency_names

    def get(self, name: str) -> Service:
        """Return a registered service by name."""
        try:
            return self._services[name]
        except KeyError as error:
            raise ServiceRegistrationError(f"Unknown service: {name}") from error

    def initialize(self) -> None:
        """Initialize services after resolving all dependencies."""
        for name in self._resolution_order():
            if name not in self._initialized:
                self._logger.debug("Initializing service '%s'", name)
                self._services[name].initialize()
                self._initialized.append(name)

    def start(self) -> None:
        """Start initialized services in dependency order."""
        self.initialize()
        for name in self._resolution_order():
            if name not in self._started:
                self._logger.debug("Starting service '%s'", name)
                self._services[name].start()
                self._started.append(name)

    def stop(self) -> None:
        """Stop started services in reverse dependency order."""
        for name in reversed(self._started):
            self._logger.debug("Stopping service '%s'", name)
            self._services[name].stop()
        self._started.clear()

    def shutdown(self) -> None:
        """Shutdown initialized services in reverse dependency order."""
        self.stop()
        for name in reversed(self._initialized):
            self._logger.debug("Shutting down service '%s'", name)
            self._services[name].shutdown()
        self._initialized.clear()

    def _resolution_order(self) -> list[str]:
        resolved: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in visiting:
                raise ServiceRegistrationError(f"Circular service dependency detected at: {name}")
            visiting.add(name)
            for dependency in self._dependencies[name]:
                if dependency not in self._services:
                    raise ServiceRegistrationError(
                        f"Service '{name}' depends on unregistered service '{dependency}'"
                    )
                visit(dependency)
            visiting.remove(name)
            visited.add(name)
            resolved.append(name)

        for service_name in self._services:
            visit(service_name)
        return resolved

    @staticmethod
    def _validate_name(name: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ServiceRegistrationError("Service name must be a non-empty string.")

    @staticmethod
    def _validate_service(service: object) -> None:
        required_methods = ("initialize", "start", "stop", "shutdown")
        missing = [method for method in required_methods if not callable(getattr(service, method, None))]
        if missing:
            raise ServiceRegistrationError(f"Service is missing lifecycle methods: {', '.join(missing)}")
