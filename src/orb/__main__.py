"""
=============================================================
ORB Platform
Package Entry Point

Allows ORB to be started using:

    python -m orb

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from orb.app import ORBApplication


def main() -> None:
    """
    Package entry point.
    """
    app = ORBApplication()
    app.run()


if __name__ == "__main__":
    main()
