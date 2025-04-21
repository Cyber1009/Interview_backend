"""
Compatibility layer for backwards compatibility.
This module forwards imports from the new location to maintain backwards compatibility.
"""
import warnings

# Forward all model imports from the new location
from app.core.database.models import *

warnings.warn(
    "Importing from app.models is deprecated. "
    "Please update your imports to use app.core.database.models instead.",
    DeprecationWarning,
    stacklevel=2
)