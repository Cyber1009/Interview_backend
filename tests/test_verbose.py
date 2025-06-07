#!/usr/bin/env python3
"""Verbose import test to catch execution errors."""

import sys
import os
import importlib.util
import traceback

# Add current directory to path
sys.path.insert(0, '.')

try:
    print("Loading module...")
    
    # Step by step import test
    print("1. Testing individual imports...")
    
    # Test FastAPI
    try:
        from fastapi import APIRouter, HTTPException, BackgroundTasks, status, Depends
        print("  ✓ FastAPI imports OK")
    except Exception as e:
        print("  ✗ FastAPI imports failed:", e)
        raise
    
    # Test other imports
    try:
        from fastapi.responses import JSONResponse
        from sqlalchemy.orm import Session
        from typing import Optional, Dict, Any
        from pydantic import BaseModel
        from datetime import datetime
        print("  ✓ Standard library imports OK")
    except Exception as e:
        print("  ✗ Standard library imports failed:", e)
        raise
    
    # Test app imports
    try:
        from app.api.dependencies import get_db
        print("  ✓ get_db import OK")
    except Exception as e:
        print("  ✗ get_db import failed:", e)
        raise
        
    try:
        from app.core.database.models import CandidateSession
        print("  ✓ CandidateSession import OK")
    except Exception as e:
        print("  ✗ CandidateSession import failed:", e)
        raise
        
    try:
        from app.services.recordings import recording_service
        print("  ✓ recording_service import OK")
    except Exception as e:
        print("  ✗ recording_service import failed:", e)
        raise
    
    print("2. All imports successful, now testing module creation...")
    
    # Create router
    try:
        enhanced_batch_router = APIRouter()
        print("  ✓ Router creation OK")
        print("  Router type:", type(enhanced_batch_router))
    except Exception as e:
        print("  ✗ Router creation failed:", e)
        raise
    
    print("3. Basic functionality test successful!")
    
except Exception as e:
    print("✗ Error during testing:", e)
    traceback.print_exc()
