#!/usr/bin/env python3
"""Execute enhanced_batch.py line by line to catch runtime errors."""

import sys
import os

# Add current directory to path
sys.path.insert(0, '.')

try:
    print("Executing enhanced_batch.py content step by step...")
    
    # Execute the actual file content
    with open('app/api/endpoints/candidates/enhanced_batch.py', 'r') as f:
        content = f.read()
    
    # Create a new namespace for execution
    namespace = {'__name__': '__main__'}
    
    print("Executing the module...")
    exec(content, namespace)
    
    print("✓ Module executed successfully")
    print("Namespace keys:", [k for k in namespace.keys() if not k.startswith('__')])
    
    if 'enhanced_batch_router' in namespace:
        print("✓ enhanced_batch_router created successfully!")
        router = namespace['enhanced_batch_router']
        print("Router type:", type(router))
        print("Number of routes:", len(router.routes))
        for route in router.routes:
            print(f"  - {route.methods} {route.path}")
    else:
        print("✗ enhanced_batch_router not found in namespace")
        
except Exception as e:
    print("✗ Error during execution:", e)
    import traceback
    traceback.print_exc()
