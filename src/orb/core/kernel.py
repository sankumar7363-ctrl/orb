"""
=============================================================
ORB Platform
Kernel

Central coordinator of the ORB Platform.

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from orb.core.lifecycle import LifecycleManager


class ORBKernel:
    """
    Core execution kernel of the ORB Platform.
    """

    def __init__(self):
        self.lifecycle = LifecycleManager()

    @property
    def state(self) -> str:
        """Return the current application state."""
        return self.lifecycle.state

    def start(self):
        """
        Start the ORB Platform.
        """

        self.lifecycle.initialize()
        self.lifecycle.start()

    def stop(self):
        """
        Stop the ORB Platform.
        """

        self.lifecycle.stop()
        self.lifecycle.shutdown()

    def is_running(self) -> bool:
        """
        Return True if ORB is running.
        """

        return self.lifecycle.is_running()