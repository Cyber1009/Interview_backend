#!/usr/bin/env python3
"""Test script to isolate enhanced_batch import issues."""

import sys
import traceback
import importlib.util
import os

sys.path.insert(0, '.')

def test_imports():
    try:
        print("Testing FastAPI import...")
        from fastapi import APIRouter
        print("✓ FastAPI imported successfully")
        
        print("Testing dependencies import...")
        from app.api.dependencies import get_db
        print("✓ Dependencies imported successfully")
        
        print("Testing models import...")
        from app.core.database.models import CandidateSession
        print("✓ Models imported successfully")
        
        print("Testing recording service import...")
        from app.services.recordings import recording_service
        print("✓ Recording service imported successfully")
        
        print("Testing router creation...")
        test_router = APIRouter()
        print("✓ Router created successfully")
        
        print("Now testing the actual enhanced_batch module...")  
        # Import the module directly to avoid circular imports
        file_path = os.path.abspath('app/api/endpoints/candidates/enhanced_batch.py')
        spec = importlib.util.spec_from_file_location('enhanced_batch', file_path)
        enhanced_batch_module = importlib.util.module_from_spec(spec)
        
        # Execute the module
        spec.loader.exec_module(enhanced_batch_module)
        print("✓ Module imported successfully")
        
        if hasattr(enhanced_batch_module, 'enhanced_batch_router'):
            print("✓ enhanced_batch_router exists in module")
            print(f"Router type: {type(enhanced_batch_module.enhanced_batch_router)}")
        else:
            print("✗ enhanced_batch_router NOT found in module")
            print(f"Module attributes: {[attr for attr in dir(enhanced_batch_module) if not attr.startswith('_')]}")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_imports()
