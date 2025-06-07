"""
Backward Compatibility Module for Error Handling

This module provides backward compatibility for the old error import paths
while the application transitions to the new consolidated structure.

DEPRECATED: This module is for backward compatibility only.
Please update imports to use:
- app.api.exceptions for all error handling
"""
import warnings

# Import everything from the new consolidated modules
from app.api.exceptions import *

# Issue deprecation warnings for old import paths
warnings.warn(
    "Importing from app.core.errors is deprecated. "
    "Please use app.api.exceptions instead.",
    DeprecationWarning,
    stacklevel=2
)
