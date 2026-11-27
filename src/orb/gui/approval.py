from __future__ import annotations

import json
from dataclasses import dataclass, field
from threading import Event, Lock
from typing import Any, Mapping

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import QMessageBox, QWidget


@dataclass
class ApprovalRequest:
    """Thread-safe response container for an approval request."""

    capability_name: str
    parameters: dict[str, Any]
    completed: Event = field(default_factory=Event, repr=False)
    approved: bool = False
    cancelled: bool = False
    _lock: Any = field(default_factory=Lock, repr=False)

    def finish(self, approved: bool) -> None:
        with self._lock:
            if self.cancelled:
                return
            self.approved = approved
            self.completed.set()

    def cancel(self) -> None:
        with self._lock:
            self.cancelled = True
            self.completed.set()

    def is_cancelled(self) -> bool:
        with self._lock:
            return self.cancelled


class QtApprovalBridge(QObject):
    """Bridge background execution requests to the GUI thread."""

    approval_requested = Signal(object)

    def __init__(
        self,
        parent: QWidget,
        timeout_seconds: int = 60,
    ) -> None:
        super().__init__(parent)

        self._dialog_parent = parent
        self._timeout_seconds = timeout_seconds

        self.approval_requested.connect(
            self._show_approval_dialog,
            Qt.ConnectionType.QueuedConnection,
        )

    def request_approval(
        self,
        capability_name: str,
        parameters: Mapping[str, Any],
    ) -> bool:
        """Request GUI approval from a background worker."""

        request = ApprovalRequest(
            capability_name=capability_name,
            parameters=dict(parameters),
        )

        self.approval_requested.emit(request)

        if not request.completed.wait(self._timeout_seconds + 5):
            request.cancel()
            return False

        return request.approved

    @Slot(object)
    def _show_approval_dialog(self, request: ApprovalRequest) -> None:
        """Display the approval dialog on the GUI thread."""

        if request.is_cancelled():
            return

        try:
            details = json.dumps(
                request.parameters,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

            if len(details) > 3000:
                details = details[:3000] + "\n...[truncated]"

            dialog = QMessageBox(self._dialog_parent)
            dialog.setWindowTitle("ORB — Approval Required")
            dialog.setIcon(QMessageBox.Icon.Warning)
            dialog.setText(
                f"ORB is requesting permission to execute:\n\n"
                f"{request.capability_name}"
            )
            dialog.setInformativeText(
                "Review the requested operation before allowing it."
            )
            dialog.setDetailedText(details)

            dialog.setStandardButtons(
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No
            )
            dialog.setDefaultButton(QMessageBox.StandardButton.No)

            timer = QTimer(dialog)
            timer.setSingleShot(True)
            timer.timeout.connect(dialog.reject)
            timer.start(self._timeout_seconds * 1000)

            result = dialog.exec()

            request.finish(
                result == QMessageBox.StandardButton.Yes
            )

        except Exception:
            request.finish(False)
