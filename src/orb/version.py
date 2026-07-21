"""
=============================================================
ORB Platform
Version Information

This module provides the official version and build information
for the ORB Platform.

Every subsystem should import version information from this file
instead of hardcoding values.

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VersionInfo:
    """
    Immutable version information for the ORB Platform.
    """

    platform_name: str
    short_name: str
    version: str
    build: str
    release_stage: str
    release_date: str
    python_requirement: str
    supported_platform: str
    author: str
    license_name: str


VERSION = VersionInfo(
    platform_name="ORB Platform",
    short_name="ORB",
    version="0.2.0",
    build="0002",
    release_stage="Alpha",
    release_date="2026-07-05",
    python_requirement="Python 3.12 or later",
    supported_platform="Windows",
    author="Santosh Kumar",
    license_name="Proprietary",
)
