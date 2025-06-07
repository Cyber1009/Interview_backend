import sys
print("Starting test...")
sys.path.insert(0, '.')

try:
    print("Testing FastAPI import...")
    from fastapi import APIRouter
    print("SUCCESS: FastAPI imported")
    
    print("Testing direct file load...")
    import importlib.util
    import os
    
    file_path = os.path.abspath('app/api/endpoints/candidates/enhanced_batch.py')
    print(f"Loading file: {file_path}")
    
    spec = importlib.util.spec_from_file_location('enhanced_batch', file_path)
    enhanced_batch_module = importlib.util.module_from_spec(spec)
    
    print("Executing module...")
    spec.loader.exec_module(enhanced_batch_module)
    print("Module executed successfully")
    
    attrs = [attr for attr in dir(enhanced_batch_module) if not attr.startswith('_')]
    print(f"Module attributes: {attrs}")
    
    if hasattr(enhanced_batch_module, 'enhanced_batch_router'):
        print("SUCCESS: enhanced_batch_router found!")
        print(f"Router type: {type(enhanced_batch_module.enhanced_batch_router)}")
    else:
        print("FAIL: enhanced_batch_router NOT found")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("Test completed")
