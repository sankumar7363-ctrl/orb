"""Build a native ORB executable for the operating system running this script.

Run this script separately on Windows, macOS, and Linux.  Native executable
formats cannot be cross-compiled reliably by PyInstaller from one host OS.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Build an ORB executable distribution using PyInstaller."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onefile", action="store_true", help="Build a single-file executable.")
    args = parser.parse_args()

    try:
        import PyInstaller.__main__
    except ImportError as error:
        message = "PyInstaller is required. Install it with: pip install '.[build]'"
        raise SystemExit(message) from error

    data_separator = ";" if os.name == "nt" else ":"
    mode = "--onefile" if args.onefile else "--onedir"
    PyInstaller.__main__.run(
        [
            "--noconfirm",
            "--clean",
            "--name",
            "orb",
            mode,
            "--paths",
            str(PROJECT_ROOT / "src"),
            "--add-data",
            f"{PROJECT_ROOT / 'configs'}{data_separator}configs",
            "--distpath",
            str(PROJECT_ROOT / "dist"),
            "--workpath",
            str(PROJECT_ROOT / "build" / "pyinstaller"),
            "--specpath",
            str(PROJECT_ROOT / "build" / "pyinstaller"),
            str(PROJECT_ROOT / "src" / "orb" / "__main__.py"),
        ]
    )


if __name__ == "__main__":
    main()
