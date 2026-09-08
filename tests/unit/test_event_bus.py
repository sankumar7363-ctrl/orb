"""Unit tests for the ORB Event Bus."""

import unittest

from orb.events import Event, EventBus
from orb.core.kernel import ORBKernel


class EventBusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()

    def test_dispatches_event_to_topic_subscribers(self) -> None:
        received: list[Event] = []
        self.bus.subscribe("kernel.started", received.append)
        event = Event("kernel.started", {"state": "RUNNING"})

        count = self.bus.publish(event)

        self.assertEqual(count, 1)
        self.assertEqual(received, [event])

    def test_wildcard_subscriber_receives_every_event(self) -> None:
        topics: list[str] = []
        self.bus.subscribe("*", lambda event: topics.append(event.topic))

        self.bus.publish(Event("kernel.started"))
        self.bus.publish(Event("kernel.stopped"))

        self.assertEqual(topics, ["kernel.started", "kernel.stopped"])

    def test_unsubscribe_removes_handler(self) -> None:
        received: list[Event] = []
        self.bus.subscribe("kernel.started", received.append)

        self.assertTrue(self.bus.unsubscribe("kernel.started", received.append))
        self.assertFalse(self.bus.unsubscribe("kernel.started", received.append))
        self.assertEqual(self.bus.publish(Event("kernel.started")), 0)
        self.assertEqual(received, [])

    def test_failed_handler_does_not_block_other_handlers(self) -> None:
        received: list[str] = []

        def failing_handler(event: Event) -> None:
            raise RuntimeError("expected failure")

        self.bus.subscribe("task.completed", failing_handler)
        self.bus.subscribe("task.completed", lambda event: received.append(event.topic))

        self.assertEqual(self.bus.publish(Event("task.completed")), 2)
        self.assertEqual(received, ["task.completed"])

    def test_event_is_immutable_and_validated(self) -> None:
        event = Event("test", {"value": 1})

        with self.assertRaises(TypeError):
            event.payload["value"] = 2
        with self.assertRaises(ValueError):
            Event(" ")
        with self.assertRaises(ValueError):
            self.bus.subscribe("", lambda ignored: None)

    def test_kernel_publishes_lifecycle_events(self) -> None:
        kernel = ORBKernel()
        received: list[str] = []
        kernel.event_bus.subscribe("*", lambda event: received.append(event.topic))

        kernel.start()
        kernel.stop()

        self.assertEqual(received, ["kernel.started", "kernel.stopped"])


if __name__ == "__main__":
    unittest.main()
