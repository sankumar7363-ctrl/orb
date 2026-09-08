# Milestone 03 - Logging System

## Status

Completed

## Delivered

- Centralized ORB logger namespace
- JSON structured console logging
- UTF-8 file logging with configurable directory and file name
- Configurable log level
- Safe logger reconfiguration without duplicate handlers
- Explicit shutdown that releases file handles on Windows
- Kernel startup and shutdown logging
- Unit-test coverage

## Configuration

```toml
[logging]
level = "INFO"
directory = "Logs"
file_name = "orb.log"
```

The logging system writes one JSON object per log line.  Configure it through
the `logging` table in `configs/orb.toml`.
