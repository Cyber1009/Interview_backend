#!/usr/bin/env python3
"""Direct import test bypassing the candidates package."""

import sys
import os
import importlib.util

# Add current directory to path
sys.path.insert(0, '.')

try:
    # Direct file import without package
    file_path = os.path.abspath('app/api/endpoints/candidates/enhanced_batch.py')
    spec = importlib.util.spec_from_file_location('enhanced_batch_direct', file_path)
    module = importlib.util.module_from_spec(spec)
    
    # Execute the module
    spec.loader.exec_module(module)
    
    print("✓ Module loaded successfully")
    print("Module attributes:", [attr for attr in dir(module) if not attr.startswith('_')])
    
    if hasattr(module, 'enhanced_batch_router'):
        print("✓ enhanced_batch_router found!")
        print("Router type:", type(module.enhanced_batch_router))
        print("Router routes:", len(module.enhanced_batch_router.routes))
    else:
        print("✗ enhanced_batch_router not found")
        
except Exception as e:
    print("✗ Error:", e)
    import traceback
    traceback.print_exc()
