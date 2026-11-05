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
        import orb.logging.manager as manager

        with tempfile.TemporaryDirectory() as directory:
            settings = {"logging": {"directory": directory}}

            try:
                logger = configure_logging(settings)

                print("\n--- BEFORE SECOND CONFIGURATION ---")
                print("Handler count:", len(logger.handlers))
                print("Registry count:", len(manager._MANAGED_HANDLERS))

                for handler in logger.handlers:
                    print(
                        type(handler).__name__,
                        id(handler),
                        handler in manager._MANAGED_HANDLERS,
                        handler.stream if isinstance(handler, logging.StreamHandler) else ""
                    )

                configure_logging(settings)

                print("\n--- AFTER SECOND CONFIGURATION ---")
                print("Handler count:", len(logger.handlers))
                print("Registry count:", len(manager._MANAGED_HANDLERS))

                for handler in logger.handlers:
                    print(
                        type(handler).__name__,
                        id(handler),
                        handler in manager._MANAGED_HANDLERS,
                    )

                orb_handlers = [
                    handler
                    for handler in logger.handlers
                    if isinstance(handler.formatter, JsonFormatter)
                ]

                self.assertEqual(len(orb_handlers), 2)

            finally:
                shutdown_logging()


if __name__ == "__main__":
    unittest.main()
