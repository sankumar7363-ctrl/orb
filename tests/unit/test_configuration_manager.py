"""Unit tests for ORB configuration management."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orb.configuration.manager import ConfigurationError, ConfigurationManager


class ConfigurationManagerTests(unittest.TestCase):
    def test_loads_defaults_when_no_file_exists(self) -> None:
        with patch("orb.configuration.manager.CONFIG_DIRECTORY", Path("missing-config-directory")):
            configuration = ConfigurationManager().load()

        self.assertIsNone(configuration.source)
        self.assertEqual(configuration.get("application.name"), "ORB")
        self.assertFalse(configuration.get("application.debug"))

    def test_file_values_are_merged_with_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orb.toml"
            path.write_text('[application]\nname = "Test ORB"\n', encoding="utf-8")
            configuration = ConfigurationManager(path).load()

        self.assertEqual(configuration.get("application.name"), "Test ORB")
        self.assertEqual(configuration.get("runtime.default_timeout"), 30)

    def test_environment_overrides_take_precedence(self) -> None:
        with patch.dict(os.environ, {"ORB_APPLICATION__DEBUG": "true"}, clear=False):
            configuration = ConfigurationManager().load()

        self.assertTrue(configuration.get("application.debug"))

    def test_invalid_values_are_rejected(self) -> None:
        with patch.dict(os.environ, {"ORB_RUNTIME__DEFAULT_TIMEOUT": "0"}, clear=False):
            with self.assertRaisesRegex(ConfigurationError, "positive integer"):
                ConfigurationManager().load()

    def test_explicit_missing_file_is_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "does not exist"):
            ConfigurationManager("does-not-exist.toml").load()

    def test_as_dict_returns_independent_mutable_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orb.toml"
            path.write_text(
                '[ai]\nmodel = "qwen2.5:3b"\n',
                encoding="utf-8",
            )
            configuration = ConfigurationManager(path).load()

        values = configuration.as_dict()
        values["ai"]["model"] = "changed-model"

        self.assertEqual(configuration.get("ai.model"), "qwen2.5:3b")
        self.assertEqual(values["ai"]["model"], "changed-model")


if __name__ == "__main__":
    unittest.main()
