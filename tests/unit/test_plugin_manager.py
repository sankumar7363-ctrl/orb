"""Unit tests for ORB plugin discovery and lifecycle management."""

import tempfile
import unittest
from pathlib import Path

from orb.plugins import PluginError, PluginManager


PLUGIN_SOURCE = '''
class TestPlugin:
    name = "example"

    def __init__(self):
        self.calls = []

    def initialize(self): self.calls.append("initialize")
    def start(self): self.calls.append("start")
    def stop(self): self.calls.append("stop")
    def shutdown(self): self.calls.append("shutdown")

PLUGIN = TestPlugin()
'''


class PluginManagerTests(unittest.TestCase):
    def test_discovers_loads_and_manages_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.py"
            path.write_text(PLUGIN_SOURCE, encoding="utf-8")
            manager = PluginManager([directory])

            self.assertEqual(manager.discover(), (path,))
            self.assertEqual(manager.load_all(), ("example",))
            plugin = manager.load_all() if False else manager._plugins["example"]
            manager.start()
            manager.shutdown()

            self.assertEqual(plugin.calls, ["initialize", "start", "stop", "shutdown"])

    def test_rejects_invalid_plugin_modules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.py"
            path.write_text("PLUGIN = object()", encoding="utf-8")
            manager = PluginManager([directory])

            with self.assertRaisesRegex(PluginError, "non-empty name"):
                manager.load(path)
            with self.assertRaisesRegex(PluginError, "does not exist"):
                manager.load(Path(directory) / "missing.py")

    def test_rejects_duplicate_plugin_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.py"
            second = Path(directory) / "second.py"
            first.write_text(PLUGIN_SOURCE, encoding="utf-8")
            second.write_text(PLUGIN_SOURCE, encoding="utf-8")
            manager = PluginManager([directory])
            manager.load(first)

            with self.assertRaisesRegex(PluginError, "already loaded"):
                manager.load(second)


if __name__ == "__main__":
    unittest.main()
