"""
ORB Platform
GUI Application
"""

from datetime import datetime

from orb.app import ORBApplication
from PySide6.QtWidgets import QApplication
from orb.models.goal import Goal
from orb.services.goal_service import GoalService


class ORBGuiApplication:
    """Bridge between the Qt GUI and the ORB application."""

    def __init__(self) -> None:
        self._qt_application = QApplication.instance() or QApplication([])
        self.orb = ORBApplication()
        self._activity: list[str] = []
        self._goal_service = GoalService()

    @property
    def state(self) -> str:
        """Return the current ORB application state."""
        return self.orb.state

    @property
    def service_count(self) -> int:
        """Return the number of registered ORB services."""
        return len(self.orb.kernel.service_manager.service_names)

    @property
    def plugin_count(self) -> int:
        """Return the number of registered ORB plugins."""
        return len(self.orb.kernel.plugin_manager.plugin_names)

    @property
    def activity(self) -> tuple[str, ...]:
        """Return recent ORB activity."""
        return tuple(self._activity)

    def start_orb(self) -> None:
        """Start the ORB backend."""

        if self.orb.is_running():
            return

        self.orb.start()
        self._record_activity("ORB started")

    def stop_orb(self) -> None:
        """Stop the ORB backend."""

        if not self.orb.is_running():
            return

        self.orb.stop()
        self._record_activity("ORB stopped")

    def _record_activity(self, message: str) -> None:
        """Record a GUI-visible ORB activity entry."""

        timestamp = datetime.now().strftime("%H:%M:%S")
        self._activity.append(f"[{timestamp}] {message}")

        # Keep the activity history lightweight.
        self._activity = self._activity[-20:]

    def run(self) -> int:
        """Start the Qt event loop."""
        return self._qt_application.exec()

    def quit(self) -> None:
        """Request GUI shutdown."""
        self._qt_application.quit()

    @property
    def goals(self) -> tuple[Goal, ...]:
        """Return all ORB goals."""

        return tuple(self._goal_service.get_goals())

    def create_goal(
        self,
        title: str,
        description: str = "",
    ) -> Goal:
        """Create and register a new ORB goal."""

        goal = self._goal_service.create_goal(
            title=title,
            description=description,
        )

        self._record_activity(
            f"Goal created: {goal.title}"
        )

        return goal