# Milestone 04 - Event Bus

## Status

Completed

## Delivered

- Immutable, typed event messages with unique IDs and UTC timestamps
- Topic-based subscriptions and event routing
- Wildcard (`*`) subscriptions for observing all events
- Subscription removal and full handler cleanup
- Ordered synchronous event dispatch
- Handler failure isolation so one failing subscriber does not block others
- Kernel lifecycle events: `kernel.started` and `kernel.stopped`
- Unit-test coverage

## Usage

```python
from orb.events import Event, EventBus

bus = EventBus()
bus.subscribe("task.completed", lambda event: print(event.payload))
bus.publish(Event("task.completed", {"task_id": "123"}))
```
