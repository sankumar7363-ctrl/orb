"""Unit tests for ORB service lifecycle management."""

import unittest

from orb.services import ServiceManager, ServiceRegistrationError


class FakeService:
    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        self.calls = calls

    def initialize(self) -> None:
        self.calls.append(f"initialize:{self.name}")

    def start(self) -> None:
        self.calls.append(f"start:{self.name}")

    def stop(self) -> None:
        self.calls.append(f"stop:{self.name}")

    def shutdown(self) -> None:
        self.calls.append(f"shutdown:{self.name}")


class ServiceManagerTests(unittest.TestCase):
    def test_manages_services_in_dependency_order(self) -> None:
        calls: list[str] = []
        manager = ServiceManager()
        manager.register("database", FakeService("database", calls))
        manager.register("api", FakeService("api", calls), dependencies=("database",))

        manager.start()
        manager.shutdown()

        self.assertEqual(
            calls,
            [
                "initialize:database", "initialize:api",
                "start:database", "start:api",
                "stop:api", "stop:database",
                "shutdown:api", "shutdown:database",
            ],
        )

    def test_start_is_idempotent(self) -> None:
        calls: list[str] = []
        manager = ServiceManager()
        manager.register("worker", FakeService("worker", calls))

        manager.start()
        manager.start()

        self.assertEqual(calls, ["initialize:worker", "start:worker"])

    def test_rejects_duplicate_missing_and_circular_dependencies(self) -> None:
        manager = ServiceManager()
        manager.register("one", FakeService("one", []))
        with self.assertRaisesRegex(ServiceRegistrationError, "already registered"):
            manager.register("one", FakeService("other", []))

        missing = ServiceManager()
        missing.register("api", FakeService("api", []), dependencies=("database",))
        with self.assertRaisesRegex(ServiceRegistrationError, "unregistered"):
            missing.start()

        circular = ServiceManager()
        circular.register("one", FakeService("one", []), dependencies=("two",))
        circular.register("two", FakeService("two", []), dependencies=("one",))
        with self.assertRaisesRegex(ServiceRegistrationError, "Circular"):
            circular.start()

    def test_get_and_invalid_service_registration(self) -> None:
        manager = ServiceManager()
        service = FakeService("worker", [])
        manager.register("worker", service)

        self.assertIs(manager.get("worker"), service)
        with self.assertRaisesRegex(ServiceRegistrationError, "Unknown"):
            manager.get("missing")
        with self.assertRaisesRegex(ServiceRegistrationError, "missing lifecycle"):
            manager.register("invalid", object())


if __name__ == "__main__":
    unittest.main()
