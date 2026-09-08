# ORB Distribution

ORB has one portable Python codebase, but native executables must be built on
their target operating system:

| Target | Build host | Release artifact |
| --- | --- | --- |
| Windows | Windows | `orb.exe` |
| macOS | macOS | `orb` binary or app bundle |
| Linux | Linux | `orb` binary |

## Development installation

```shell
python -m pip install -e .
orb
```

## Native executable builds

On each target platform, install ORB with its build tools and run:

```shell
python -m pip install ".[build]"
python scripts/build_executable.py
```

The output is placed in `dist/`. Use `--onefile` when a single executable is
preferred; the default `--onedir` mode starts faster. Both modes bundle the
default `configs/` directory inside the release.

## Runtime files

The executable reads its packaged default configuration from `configs/`.
Runtime data is stored in `~/.orb/` by default, including logs in
`~/.orb/logs/`. Set `ORB_HOME` to choose another writable runtime directory;
set `ORB_CONFIG` to choose a custom configuration file. A custom `[logging]`
`directory` may override the default log location.
