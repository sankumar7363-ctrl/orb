"""
=============================================================
ORB Platform
Application

Main application object for the ORB Platform.

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from orb.banner import print_banner
from orb.core.kernel import ORBKernel
from threading import Event


class ORBApplication:
    """
    Main ORB application.
    """

    def __init__(self, config_path: str | None = None):
        self.kernel = ORBKernel(config_path)

    @property
    def state(self) -> str:
        """
        Return the current application state.
        """
        return self.kernel.state

    def start(self):
        """
        Start the ORB Platform.
        """
        print_banner()
        self.kernel.start()

    def run(self) -> None:
        """Run ORB until the user requests shutdown with Ctrl+C."""
        self.start()
        print("ORB is running. Press Ctrl+C to stop.")
        try:
            Event().wait()
        except KeyboardInterrupt:
            print("\nStopping ORB...")
        finally:
            self.stop()

    def stop(self) -> None:
        """
        Stop the ORB Platform.
        """
        self.kernel.stop()

    def is_running(self) -> bool:
        """
        Return True if ORB is running.
        """
        return self.kernel.is_running()
