"""
=============================================================
ORB Platform
Lifecycle Manager

Controls the lifecycle of the ORB Platform.

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from orb.core.constants import (
    STATE_CREATED,
    STATE_INITIALIZING,
    STATE_RUNNING,
    STATE_STOPPING,
    STATE_STOPPED,
)


class LifecycleManager:
    """
    Controls the application lifecycle.
    """

    def __init__(self):
        self._state = STATE_CREATED

    @property
    def state(self) -> str:
        """Return the current lifecycle state."""
        return self._state

    def initialize(self):
        """Transition to INITIALIZING state."""
        self._state = STATE_INITIALIZING

    def start(self):
        """Transition to RUNNING state."""
        self._state = STATE_RUNNING

    def stop(self):
        """Transition to STOPPING state."""
        self._state = STATE_STOPPING

    def shutdown(self):
        """Transition to STOPPED state."""
        self._state = STATE_STOPPED

    def is_running(self) -> bool:
        """Return True if ORB is currently running."""
        return self._state == STATE_RUNNING