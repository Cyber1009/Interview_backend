#!/usr/bin/env python3
"""Test the enhanced_batch_router import after fixing circular dependency."""

try:
    from app.api.endpoints.candidates.enhanced_batch import enhanced_batch_router
    print("✓ Import successful - Router type:", type(enhanced_batch_router))
    print("✓ Router has", len(enhanced_batch_router.routes), "routes")
except Exception as e:
    print("✗ Import failed:", e)
    import traceback
    traceback.print_exc()
