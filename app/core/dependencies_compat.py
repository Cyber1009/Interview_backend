"""
Backward Compatibility Module for Dependencies

This module provides backward compatibility for the old dependency import paths
while the application transitions to the new consolidated structure.

DEPRECATED: This module is for backward compatibility only.
Please update imports to use:
- app.api.dependencies for all dependencies
- app.api.exceptions for all error handling
"""
import warnings

# Import everything from the new consolidated modules
from app.api.dependencies import *
from app.api.exceptions import *

# Issue deprecation warnings for old import paths
warnings.warn(
    "Importing from app.core.dependencies is deprecated. "
    "Please use app.api.dependencies instead.",
    DeprecationWarning,
    stacklevel=2
)
