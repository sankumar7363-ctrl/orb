"""A lightweight in-process event bus for loosely coupled ORB components."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any
from uuid import uuid4

from orb.logging import get_logger

EventHandler = Callable[["Event"], None]


@dataclass(frozen=True, slots=True)
class Event:
    """An immutable message published through the ORB Event Bus."""

    topic: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.topic or not self.topic.strip():
            raise ValueError("Event topic must be a non-empty string.")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


class EventBus:
    """Publish events to exact-topic and wildcard-topic subscribers.

    A ``*`` subscription receives every event.  Handlers are called in their
    subscription order.  A handler failure is logged and does not prevent the
    remaining handlers from receiving the event.
    """

    WILDCARD_TOPIC = "*"

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._logger = get_logger("events")

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Register *handler* to receive events published to *topic*."""
        self._validate_topic(topic)
        if not callable(handler):
            raise TypeError("Event handler must be callable.")
        if handler not in self._handlers[topic]:
            self._handlers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: EventHandler) -> bool:
        """Remove a subscription and return whether it existed."""
        self._validate_topic(topic)
        handlers = self._handlers.get(topic)
        if not handlers or handler not in handlers:
            return False
        handlers.remove(handler)
        if not handlers:
            del self._handlers[topic]
        return True

    def publish(self, event: Event) -> int:
        """Dispatch *event* and return the number of handlers invoked."""
        if not isinstance(event, Event):
            raise TypeError("Only Event instances can be published.")
        handlers = [*self._handlers.get(event.topic, ()), *self._handlers.get(self.WILDCARD_TOPIC, ())]
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                self._logger.exception("Event handler failed for topic '%s'", event.topic)
        return len(handlers)

    def clear(self) -> None:
        """Remove every registered event handler."""
        self._handlers.clear()

    @staticmethod
    def _validate_topic(topic: str) -> None:
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("Event topic must be a non-empty string.")
