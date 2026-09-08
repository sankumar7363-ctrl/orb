"""
=============================================================
ORB Platform
Core Constants

Central location for constants used throughout the ORB Platform.

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

import os
import sys
from pathlib import Path

# =============================================================
# APPLICATION
# =============================================================

APPLICATION_NAME = "ORB Platform"
APPLICATION_SHORT_NAME = "ORB"

# =============================================================
# LIFECYCLE STATES
# =============================================================

STATE_CREATED = "CREATED"
STATE_INITIALIZING = "INITIALIZING"
STATE_RUNNING = "RUNNING"
STATE_STOPPING = "STOPPING"
STATE_STOPPED = "STOPPED"

# =============================================================
# EXIT CODES
# =============================================================

EXIT_SUCCESS = 0
EXIT_FAILURE = 1

# =============================================================
# DEFAULT DIRECTORIES
# =============================================================

if getattr(sys, "frozen", False):
    # PyInstaller exposes bundled assets through its temporary/runtime path.
    PROJECT_ROOT = Path(sys.executable).resolve().parent
    BUNDLE_DIRECTORY = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    BUNDLE_DIRECTORY = PROJECT_ROOT

USER_DATA_DIRECTORY = Path(os.getenv("ORB_HOME", Path.home() / ".orb"))

CONFIG_DIRECTORY = BUNDLE_DIRECTORY / "configs"
LOG_DIRECTORY = USER_DATA_DIRECTORY / "logs"
DATA_DIRECTORY = USER_DATA_DIRECTORY / "data"
CACHE_DIRECTORY = USER_DATA_DIRECTORY / "cache"
MEMORY_DIRECTORY = USER_DATA_DIRECTORY / "memory"

# =============================================================
# CONFIGURATION
# =============================================================

DEFAULT_CONFIG_FILE = "orb.toml"

# =============================================================
# LOGGING
# =============================================================

DEFAULT_LOG_LEVEL = "INFO"

# =============================================================
# TIMEOUTS
# =============================================================

DEFAULT_TIMEOUT = 30
