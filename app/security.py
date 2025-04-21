"""
Compatibility layer for backwards compatibility.
This module forwards imports from the new location to maintain backwards compatibility.
"""
import warnings

# Forward all security imports from the new location
from app.core.security.auth import *
from app.core.security.bcrypt_fix import *

warnings.warn(
    "Importing from app.security is deprecated. "
    "Please update your imports to use app.core.security modules instead.",
    DeprecationWarning,
    stacklevel=2
)