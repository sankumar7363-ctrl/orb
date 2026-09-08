# Milestone 05 - Service Manager

## Status

Completed

## Delivered

- Service registration with unique names
- Lifecycle validation for initialized, started, stopped, and shutdown services
- Dependency-aware initialization and startup order
- Reverse-order stopping and shutdown
- Detection of missing and circular dependencies
- Idempotent startup and clean shutdown behavior
- Kernel lifecycle integration and unit-test coverage

## Usage

```python
from orb.services import ServiceManager

services = ServiceManager()
services.register("database", database_service)
services.register("api", api_service, dependencies=("database",))
services.start()
services.shutdown()
```
