"""
=============================================================
ORB Platform
Development Entry Point

Run using:

    python main.py

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from orb.app import ORBApplication


def main() -> None:
    """
    Development entry point.
    """
    app = ORBApplication()
    app.run()


if __name__ == "__main__":
    main()
