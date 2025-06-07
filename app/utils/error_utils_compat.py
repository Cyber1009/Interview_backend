"""
Backward Compatibility Module for Utils Error Handling

This module provides backward compatibility for the old utils error import paths
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
    "Importing from app.utils.error_utils is deprecated. "
    "Please use app.api.exceptions instead.",
    DeprecationWarning,
    stacklevel=2
)
