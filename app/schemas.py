"""
Compatibility layer for backwards compatibility.
This module forwards imports from the new location to maintain backwards compatibility.
"""
import warnings

# Forward all schema imports from the new location
from app.schemas.admin_schemas import *
from app.schemas.auth_schemas import *
from app.schemas.interview_schemas import *
from app.schemas.payment_schemas import *
from app.schemas.recording_schemas import *
from app.schemas.theme_schemas import *

warnings.warn(
    "Importing from app.schemas is deprecated. "
    "Please update your imports to use specific schema modules from app.schemas instead.",
    DeprecationWarning,
    stacklevel=2
)
