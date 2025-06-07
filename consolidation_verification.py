#!/usr/bin/env python3
"""
Consolidation Verification Script

This script verifies that the consolidation of dependencies and exceptions
was successful and all imports work correctly.
"""

def test_dependencies_import():
    """Test that all dependencies can be imported successfully"""
    try:
        from app.api.dependencies import (
            db_dependency,
            user_dependency, 
            active_user_dependency,
            interviewer_dependency,
            admin_dependency,
            verification_service_dependency,
            session_service_dependency,
            recording_service_dependency,
            reporting_service_dependency
        )
        print("✅ Dependencies import: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ Dependencies import: FAILED - {e}")
        return False

def test_exceptions_import():
    """Test that all exceptions can be imported successfully"""
    try:
        from app.api.exceptions import (
            not_found,
            bad_request, 
            forbidden,
            unauthorized,
            internal_error,
            payment_error,
            validation_error,
            APIError,
            create_error_response,
            setup_exception_handlers
        )
        print("✅ Exceptions import: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ Exceptions import: FAILED - {e}")
        return False

def test_main_app_import():
    """Test that the main app can be imported with consolidated modules"""
    try:
        from app.main import app
        print("✅ Main app import: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ Main app import: FAILED - {e}")
        return False

def test_api_endpoints_import():
    """Test that API endpoints can import consolidated modules"""
    try:
        # Test a few key endpoints
        from app.api.endpoints.auth import registration
        from app.api.endpoints.interviewer import interviews
        print("✅ API endpoints import: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ API endpoints import: FAILED - {e}")
        return False

def run_consolidation_verification():
    """Run all verification tests"""
    print("🔍 CONSOLIDATION VERIFICATION")
    print("=" * 50)
    
    tests = [
        test_dependencies_import,
        test_exceptions_import, 
        test_main_app_import,
        test_api_endpoints_import
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 CONSOLIDATION SUCCESSFUL!")
        print("\n✨ Redundancy elimination completed:")
        print("  • app.core.dependencies → app.api.dependencies")
        print("  • app.api.deps → app.api.dependencies") 
        print("  • app.api.deps_services → app.api.dependencies")
        print("  • app.core.errors → app.api.exceptions")
        print("  • app.utils.error_utils → app.api.exceptions")
        
        print("\n🧹 Clean up next steps:")
        print("  1. Remove old dependency files after full verification")
        print("  2. Update any remaining import references")
        print("  3. Test all endpoints to ensure functionality")
        
        return True
    else:
        print("⚠️  Some tests failed. Review errors above.")
        return False

if __name__ == "__main__":
    run_consolidation_verification()
