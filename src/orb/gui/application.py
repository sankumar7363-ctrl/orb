"""ORB Platform - GUI Application Bridge."""

from __future__ import annotations

from collections import deque
from datetime import datetime
import logging
import sys
from typing import Sequence

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from orb.app import ORBApplication
from orb.models.goal import Goal
from orb.services.goal_service import GoalService

logger = logging.getLogger(__name__)


class ORBGuiApplication(QObject):
    """Bridge between the PySide6 GUI event loop and the ORB backend engine."""

    # Reactive signals for UI components
    activity_recorded = Signal(str)
    orb_state_changed = Signal(str)
    goal_created_signal = Signal(Goal)

    MAX_ACTIVITY_LOGS = 50

    def __init__(self, sys_argv: list[str] | None = None) -> None:
        super().__init__()

        # Ensure a singleton QApplication instance exists
        self._qt_application = QApplication.instance() or QApplication(
            sys_argv or sys.argv
        )

        # Core services
        self.orb = ORBApplication()
        self._goal_service = GoalService()

        # Activity ring-buffer
        self._activity: deque[str] = deque(maxlen=self.MAX_ACTIVITY_LOGS)

        # Wire clean shutdown on Qt app exit
        self._qt_application.aboutToQuit.connect(self._handle_shutdown)

    # -------------------------------------------------------------------------
    # Properties & Status
    # -------------------------------------------------------------------------

    @property
    def state(self) -> str:
        """Return the current ORB application state."""
        return self.orb.state

    @property
    def is_running(self) -> bool:
        """Return whether the backend ORB engine is running."""
        return self.orb.is_running()

    @property
    def service_count(self) -> int:
        """Return the number of registered ORB kernel services."""
        try:
            return len(self.orb.kernel.service_manager.service_names)
        except AttributeError:
            return 0

    @property
    def plugin_count(self) -> int:
        """Return the number of registered ORB kernel plugins."""
        try:
            return len(self.orb.kernel.plugin_manager.plugin_names)
        except AttributeError:
            return 0

    @property
    def activity(self) -> tuple[str, ...]:
        """Return an immutable snapshot of recent ORB activities."""
        return tuple(self._activity)

    @property
    def goals(self) -> tuple[Goal, ...]:
        """Return all available goals."""
        try:
            return tuple(self._goal_service.get_goals())
        except Exception:
            logger.exception("Failed to fetch goals from GoalService.")
            return ()

    # -------------------------------------------------------------------------
    # ORB Engine Control
    # -------------------------------------------------------------------------

    def start_orb(self) -> bool:
        """Start the ORB backend engine. Returns True if started successfully."""
        if self.is_running:
            logger.warning("ORB start requested, but it is already running.")
            return False

        try:
            self.orb.start()
            self._record_activity("ORB engine started")
            self.orb_state_changed.emit(self.state)
            return True
        except Exception as err:
            logger.exception("Failed to start ORB engine.")
            self._record_activity(f"Error starting ORB: {err}")
            return False

    def stop_orb(self) -> bool:
        """Stop the ORB backend engine. Returns True if stopped successfully."""
        if not self.is_running:
            logger.warning("ORB stop requested, but it is not running.")
            return False

        try:
            self.orb.stop()
            self._record_activity("ORB engine stopped")
            self.orb_state_changed.emit(self.state)
            return True
        except Exception as err:
            logger.exception("Failed to stop ORB engine.")
            self._record_activity(f"Error stopping ORB: {err}")
            return False

    # -------------------------------------------------------------------------
    # Goal Management
    # -------------------------------------------------------------------------

    def create_goal(self, title: str, description: str = "") -> Goal | None:
        """Create and register a new ORB goal."""
        title_clean = title.strip()
        if not title_clean:
            raise ValueError("Goal title cannot be empty.")

        try:
            goal = self._goal_service.create_goal(
                title=title_clean,
                description=description.strip(),
            )
            self._record_activity(f"Goal created: {goal.title}")
            self.goal_created_signal.emit(goal)
            return goal
        except Exception:
            logger.exception("Failed to create goal '%s'.", title)
            return None

    # -------------------------------------------------------------------------
    # Helpers & Lifecycle
    # -------------------------------------------------------------------------

    def _record_activity(self, message: str) -> None:
        """Record an activity item and emit an update to UI listeners."""
        entry = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self._activity.append(entry)
        self.activity_recorded.emit(entry)

    def _handle_shutdown(self) -> None:
        """Internal cleanup handler invoked before Qt terminates."""
        if self.is_running:
            logger.info("Application shutting down: stopping ORB engine...")
            self.stop_orb()

    def run(self) -> int:
        """Start the Qt event loop."""
        return self._qt_application.exec()

    def quit(self) -> None:
        """Request application termination."""
        self._qt_application.quit()