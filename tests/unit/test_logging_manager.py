"""Unit tests for ORB logging configuration."""

import json
import logging
import tempfile
import unittest
from pathlib import Path

from orb.logging.manager import JsonFormatter, configure_logging, get_logger, shutdown_logging


class LoggingManagerTests(unittest.TestCase):
    def test_configures_console_and_file_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            try:
                logger = configure_logging(
                    {"logging": {"level": "DEBUG", "directory": directory, "file_name": "test.log"}}
                )
                logger.debug("logging is ready")

                self.assertEqual(logger.level, logging.DEBUG)
                log_file = Path(directory) / "test.log"
                self.assertTrue(log_file.exists())
                payload = json.loads(log_file.read_text(encoding="utf-8").strip())
                self.assertEqual(payload["message"], "logging is ready")
                self.assertEqual(payload["level"], "DEBUG")
            finally:
                shutdown_logging()

    def test_reconfiguration_does_not_duplicate_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = {"logging": {"directory": directory}}
            try:
                logger = configure_logging(settings)
                configure_logging(settings)

                self.assertEqual(len(logger.handlers), 2)
            finally:
                shutdown_logging()

    def test_component_logger_uses_orb_namespace(self) -> None:
        self.assertEqual(get_logger("events").name, "orb.events")

    def test_json_formatter_includes_core_fields(self) -> None:
        record = logging.LogRecord("orb", logging.INFO, __file__, 1, "hello %s", ("world",), None)
        payload = json.loads(JsonFormatter().format(record))

        self.assertEqual(payload["message"], "hello world")
        self.assertEqual(payload["logger"], "orb")
        self.assertIn("timestamp", payload)


if __name__ == "__main__":
    unittest.main()
