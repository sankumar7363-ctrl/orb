# Milestone 02 - Configuration Manager

## Status

Completed

## Delivered

- TOML configuration loading from `configs/orb.toml`
- Safe defaults when no default file is present
- Nested configuration merging
- Environment overrides using `ORB_<SECTION>__<KEY>`
- Validation for application identity, debug mode, and runtime timeout
- An immutable `Configuration` snapshot with dotted-path lookup
- Kernel startup integration and unit-test coverage

## Usage

```toml
[application]
name = "ORB"
environment = "production"
debug = false

[runtime]
default_timeout = 30
```

Set `ORB_CONFIG` to use a different TOML file. Environment variables take
precedence over file values, for example `ORB_APPLICATION__DEBUG=true`.
