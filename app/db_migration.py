"""
Compatibility layer for backwards compatibility.
This module forwards imports from the new location to maintain backwards compatibility.
"""
import warnings

# Forward all migration imports from the new location
from app.core.database.migrations import *

# Log deprecation warning
warnings.warn(
    "Importing from app.db_migration is deprecated. "
    "Please update your imports to use app.core.database.migrations instead.",
    DeprecationWarning,
    stacklevel=2
)
