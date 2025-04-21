"""
Schema package for the Interview Management Platform.

This package contains all Pydantic models used for request validation,
response serialization, and data transfer between API layers.

Schemas are organized by domain:
- auth_schemas: Authentication and user schemas
- interview_schemas: Interview, questions, and tokens schemas
- recording_schemas: Recording and transcription schemas
- payment_schemas: Payment and subscription schemas
- theme_schemas: Customization and theming schemas
- admin_schemas: Administrative schemas
"""

# Re-export schemas from domain-specific modules for easy access
from app.schemas.auth_schemas import *
from app.schemas.interview_schemas import *
from app.schemas.recording_schemas import *
from app.schemas.payment_schemas import *
from app.schemas.theme_schemas import *
from app.schemas.admin_schemas import *

# This provides a clean import experience:
# from app.schemas import UserCreate, TokenData, etc.