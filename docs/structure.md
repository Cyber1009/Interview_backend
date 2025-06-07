# Interview Backend Project Structure

This document provides an overview of the Interview Backend application structure. The project follows a modular structure to improve organization, maintainability, and scalability.

## Directory Structure

```
app/                            # Main application package
├── api/                        # API-related code
│   ├── deps.py                 # Dependency injection utilities
│   ├── router.py               # Main API router
│   └── endpoints/              # API endpoint modules
│       ├── admin/              # Admin-related endpoints
│       ├── auth/               # Authentication endpoints
│       ├── candidates/         # Candidate-facing endpoints
│       ├── interviewer/        # Interviewer-facing endpoints
│       ├── payments/           # Payment & subscription endpoints
│       └── system/             # System endpoints
├── core/                       # Core application modules
│   ├── config.py               # Application configuration
│   ├── database/               # Database-related modules
│   │   ├── db.py               # Database connection and session
│   │   ├── migrations.py       # Database migration utilities
│   │   └── models.py           # SQLAlchemy models
│   ├── processors/             # Background processors
│   │   ├── analysis_processor.py  # Interview analysis tools
│   │   └── transcription_processor.py  # Audio transcription
│   └── security/               # Security-related modules
│       ├── auth.py             # Authentication & authorization 
│       └── bcrypt_fix.py       # BCrypt compatibility fixes
├── schemas/                    # Pydantic schema models
│   ├── admin_schemas.py        # Admin-related schemas
│   ├── auth_schemas.py         # Authentication schemas
│   ├── interview_schemas.py    # Interview schemas
│   ├── payment_schemas.py      # Payment schemas
│   ├── recording_schemas.py    # Recording schemas
│   └── theme_schemas.py        # UI theme schemas
├── utils/                      # Utility functions
│   ├── datetime_utils.py       # Date and time utilities
│   ├── db_utils.py             # Database utilities
│   ├── error_utils.py          # Error handling utilities
│   └── subscription_utils.py   # Subscription management utilities
├── database.py                 # Compatibility layer -> core/database/db.py
├── db_migration.py             # Compatibility layer -> core/database/migrations.py
├── models.py                   # Compatibility layer -> core/database/models.py
├── schemas.py                  # Compatibility layer -> schemas/*
├── security.py                 # Compatibility layer -> core/security/*
└── main.py                     # Application entry point
```

## Key Components

### API Module (`app/api/`)
Contains all API routes and endpoints organized by functional area. Each subdirectory in `endpoints/` represents a logical grouping of related functionality.

### Core Module (`app/core/`)
Contains core application functionality including:
- Database connections and models
- Security and authentication
- Configuration management
- Processing utilities

### Schemas Module (`app/schemas/`)
Contains Pydantic models used for:
- Request validation
- Response serialization
- Data transformation

### Utils Module (`app/utils/`)
Contains utility functions that provide common functionality across the application.

### Compatibility Layers
The top-level modules like `models.py`, `schemas.py`, etc. are compatibility layers that forward imports from the new structure. These exist to maintain backward compatibility while encouraging migration to the new structure.

## Design Principles

1. **Separation of Concerns**: Code is organized based on functionality
2. **Modularity**: Related functionality is grouped together
3. **Discoverability**: Clear naming and organization makes code easy to navigate
4. **Scalability**: Structure can accommodate growth in features and complexity

## Migration Notes

The project is transitioning from a flat structure to a more hierarchical one. When working with the codebase:

1. Use imports from the new structure (e.g., `app.core.database.models` instead of `app.models`)
2. Update existing code to use the new import paths when making changes
3. The compatibility layers will be removed in a future version

## Import Guidelines

### Old Import Path (Deprecated) → New Import Path
- `from app.models import X` → `from app.core.database.models import X`
- `from app.database import X` → `from app.core.database.db import X`
- `from app.security import X` → `from app.core.security.auth import X` or `from app.core.security.bcrypt_fix import X`
- `from app.schemas import X` → `from app.schemas.{specific_schema_module} import X`
- `from app.db_migration import X` → `from app.core.database.migrations import X`
- `from app.config import X` → `from app.core.config import X`