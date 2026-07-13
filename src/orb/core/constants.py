"""
=============================================================
ORB Platform
Core Constants

Central location for constants used throughout the ORB Platform.

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

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

PROJECT_ROOT = Path.cwd()

CONFIG_DIRECTORY = PROJECT_ROOT / "configs"
LOG_DIRECTORY = PROJECT_ROOT / "Logs"
DATA_DIRECTORY = PROJECT_ROOT / "Data"
CACHE_DIRECTORY = PROJECT_ROOT / "Cache"
MEMORY_DIRECTORY = PROJECT_ROOT / "Memory"

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