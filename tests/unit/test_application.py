"""Unit tests for ORB application execution."""

import unittest
from unittest.mock import patch

from orb.app import ORBApplication


class _InterruptingWait:
    def wait(self) -> None:
        raise KeyboardInterrupt


class ApplicationTests(unittest.TestCase):
    def test_run_stops_cleanly_after_keyboard_interrupt(self) -> None:
        app = ORBApplication()
        with patch("orb.app.Event", return_value=_InterruptingWait()):
            app.run()

        self.assertEqual(app.state, "STOPPED")


if __name__ == "__main__":
    unittest.main()
