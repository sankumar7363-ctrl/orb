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


class ORBApplication:
    """
    Main ORB application.
    """

    def __init__(self):
        self.kernel = ORBKernel()

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

    def stop(self):
        """
        Stop the ORB Platform.
        """
        self.kernel.stop()

    def is_running(self) -> bool:
        """
        Return True if ORB is running.
        """
        return self.kernel.is_running()