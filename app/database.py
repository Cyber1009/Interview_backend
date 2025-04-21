"""
Compatibility layer for backwards compatibility.
This module forwards imports from the new location to maintain backwards compatibility.
"""
import warnings

# Forward all database imports from the new location
from app.core.database.db import *

warnings.warn(
    "Importing from app.database is deprecated. "
    "Please update your imports to use app.core.database.db instead.",
    DeprecationWarning,
    stacklevel=2
)