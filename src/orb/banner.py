"""
=============================================================
ORB Platform
Startup Banner

Displays the startup banner for the ORB Platform.

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from orb.version import VERSION


def get_banner() -> str:
    """
    Return the formatted startup banner.
    """

    return f"""
============================================================
                     {VERSION.platform_name}
============================================================

Version           : {VERSION.version}
Build             : {VERSION.build}
Release Stage     : {VERSION.release_stage}
Python            : {VERSION.python_requirement}
Platform          : {VERSION.supported_platform}

Author            : {VERSION.author}

============================================================
Initializing ORB Platform...
============================================================
"""


def print_banner() -> None:
    """
    Print the ORB startup banner.
    """

    print(get_banner())