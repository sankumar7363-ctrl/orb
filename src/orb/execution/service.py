from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from orb.execution.applications import ApplicationNotInstalledError
from orb.logging import get_logger


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    CAPABILITY_NOT_FOUND = "capability_not_found"
    PERMISSION_DENIED = "permission_denied"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_DENIED = "approval_denied"
    NOT_AVAILABLE = "not_available"
    EXECUTION_FAILED = "execution_failed"
    VERIFICATION_FAILED = "verification_failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionResult:
    status: ExecutionStatus
    output: Any = None
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.status is ExecutionStatus.SUCCESS


class CapabilityHandler(Protocol):
    def execute(self, parameters: Mapping[str, Any]) -> Any:
        """Execute the registered capability."""

    def verify(
        self,
        parameters: Mapping[str, Any],
        output: Any,
    ) -> bool:
        """Verify the actual execution result."""


@dataclass(frozen=True)
class CapabilityRegistration:
    name: str
    handler: CapabilityHandler
    required_permission: str
    requires_approval: bool


PermissionChecker = Callable[[str, dict[str, Any]], bool]
ApprovalHandler = Callable[[str, dict[str, Any]], bool]


class ExecutionService:
    """Execute registered ORB capabilities through safety checks."""

    def __init__(
        self,
        permission_checker: PermissionChecker | None = None,
        approval_handler: ApprovalHandler | None = None,
    ) -> None:
        self._logger = get_logger("execution.service")
        self._permission_checker = permission_checker
        self._approval_handler = approval_handler
        self._capabilities: dict[str, CapabilityRegistration] = {}

    def initialize(self) -> None:
        self._logger.info("Execution Service initialized.")

    def start(self) -> None:
        self._logger.info(
            "Execution Service started with %d capabilities.",
            len(self._capabilities),
        )

    def stop(self) -> None:
        self._logger.info("Execution Service stopped.")

    def shutdown(self) -> None:
        self._capabilities.clear()
        self._logger.info("Execution Service shutdown.")

    def set_approval_handler(
        self,
        handler: ApprovalHandler | None,
    ) -> None:
        """Configure the user approval callback."""
        if handler is not None and not callable(handler):
            raise TypeError("Approval handler must be callable.")

        self._approval_handler = handler
        self._logger.info(
            "Approval handler %s.",
            "configured" if handler else "removed",
        )

    def register_capability(
        self,
        name: str,
        handler: CapabilityHandler,
        *,
        required_permission: str,
        requires_approval: bool = False,
    ) -> None:
        """Register an explicitly supported capability."""

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Capability name must not be empty.")

        if name in self._capabilities:
            raise ValueError(f"Capability already registered: {name}")

        if not isinstance(required_permission, str) or not required_permission.strip():
            raise ValueError("A required permission must be specified.")

        if not callable(getattr(handler, "execute", None)):
            raise TypeError("Capability handler must implement execute().")

        if not callable(getattr(handler, "verify", None)):
            raise TypeError("Capability handler must implement verify().")

        self._capabilities[name] = CapabilityRegistration(
            name=name,
            handler=handler,
            required_permission=required_permission,
            requires_approval=requires_approval,
        )

        self._logger.info("Registered capability: %s", name)

    def execute(
        self,
        capability_name: str,
        parameters: Mapping[str, Any],
        *,
        cancelled: Callable[[], bool] | None = None,
    ) -> ExecutionResult:
        """Execute a capability only after permission and approval checks."""

        registration = self._capabilities.get(capability_name)

        if registration is None:
            self._logger.warning(
                "Rejected unknown capability: %s",
                capability_name,
            )
            return ExecutionResult(
                status=ExecutionStatus.CAPABILITY_NOT_FOUND,
                error=f"Unknown capability: {capability_name}",
            )

        if not isinstance(parameters, Mapping):
            return ExecutionResult(
                status=ExecutionStatus.EXECUTION_FAILED,
                error="Capability parameters must be a mapping.",
            )

        params = dict(parameters)

        # Permission checks are fail-closed.
        if self._permission_checker is None:
            return ExecutionResult(
                status=ExecutionStatus.PERMISSION_DENIED,
                error="No permission checker is configured.",
            )

        try:
            permitted = self._permission_checker(
                registration.required_permission,
                params,
            )
        except Exception as error:
            self._logger.error("Permission check failed: %s", error)
            return ExecutionResult(
                status=ExecutionStatus.PERMISSION_DENIED,
                error="Permission check could not be completed.",
            )

        if not permitted:
            self._logger.warning(
                "Permission denied for capability: %s",
                capability_name,
            )
            return ExecutionResult(
                status=ExecutionStatus.PERMISSION_DENIED,
                error=f"Permission denied: {registration.required_permission}",
            )

        # Protected actions cannot execute without an approval mechanism.
        if registration.requires_approval:
            if self._approval_handler is None:
                return ExecutionResult(
                    status=ExecutionStatus.APPROVAL_REQUIRED,
                    error="User approval is required before execution.",
                )

            try:
                approved = self._approval_handler(capability_name, params)
            except Exception as error:
                self._logger.error("Approval handling failed: %s", error)
                approved = False

            if not approved:
                self._logger.warning(
                    "Approval denied for capability: %s",
                    capability_name,
                )
                return ExecutionResult(
                    status=ExecutionStatus.APPROVAL_DENIED,
                    error="Execution was not approved.",
                )

        if cancelled is not None and cancelled():
            return ExecutionResult(
                status=ExecutionStatus.CANCELLED,
                error="Cancelled before execution.",
            )

        # Only registered handlers can reach this point.
        try:
            output = registration.handler.execute(params)
        except ApplicationNotInstalledError as error:
            self._logger.warning(
                "Capability target unavailable for %s: %s",
                capability_name,
                error,
            )
            return ExecutionResult(
                status=ExecutionStatus.NOT_AVAILABLE,
                error=str(error),
            )
        except Exception as error:
            self._logger.exception(
                "Capability execution failed: %s",
                capability_name,
            )
            return ExecutionResult(
                status=ExecutionStatus.EXECUTION_FAILED,
                error=str(error),
            )

        try:
            verified = registration.handler.verify(params, output)
        except Exception as error:
            self._logger.exception(
                "Capability verification failed: %s",
                capability_name,
            )
            verified = False

        if not verified:
            self._logger.error(
                "Capability verification failed: %s",
                capability_name,
            )
            return ExecutionResult(
                status=ExecutionStatus.VERIFICATION_FAILED,
                output=output,
                error="The execution result could not be verified.",
            )

        self._logger.info(
            "Capability executed and verified: %s",
            capability_name,
        )

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output=output,
        )

    @property
    def capability_names(self) -> frozenset[str]:
        return frozenset(self._capabilities)

    def capability_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "name": entry.name,
                "description": entry.handler.__doc__ or "",
                "permission": entry.required_permission,
                "requires_approval": entry.requires_approval,
                "parameters": getattr(type(entry.handler), "parameters", {}),
            }
            for entry in self._capabilities.values()
        ]
