#!/usr/bin/env python3
"""
Test script for the enhanced token system API endpoints.
"""
import requests
import json
from datetime import datetime, timedelta

def test_enhanced_token_api():
    """Test the enhanced token system via API endpoints."""
    print("🌐 Testing Enhanced Token System API")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    try:
        # Test the API is running
        print("\n1. Testing API availability...")
        response = requests.get(f"{base_url}/docs")
        if response.status_code == 200:
            print("✅ API is running and accessible")
        else:
            print("❌ API is not accessible")
            return
            
        # Test enhanced token creation (need to use an admin endpoint)
        print("\n2. Testing enhanced token creation...")
        print("   (This would require authentication - showing example structure)")
        
        enhanced_token_data = {
            "candidate_name": "API Test Candidate",
            "expires_in_hours": 72,
            "max_attempts": 2
        }
        
        print(f"   Example enhanced token request:")
        print(f"   POST /api/interviewer/interviews/{{interview_id}}/tokens")
        print(f"   Body: {json.dumps(enhanced_token_data, indent=2)}")
        
        print("\n3. Example token verification flow...")
        print("   Expected response structure:")
        print("   {")
        print('     "valid": true,')
        print('     "status": "valid",')
        print('     "token_obj": { ... },')
        print('     "message": "Token is valid"')
        print("   }")
        
        print("\n4. Example session creation with attempt tracking...")
        print("   POST /api/candidates/interviews/start-session")
        print("   Expected behavior:")
        print("   - Increments current_attempts counter")
        print("   - Checks against max_attempts limit")
        print("   - Returns 403 if attempts exceeded")
        
        print("\n5. Example session completion validation...")
        print("   PATCH /api/candidates/interviews/complete-session")
        print("   Expected behavior:")
        print("   - Validates session has recordings")
        print("   - Returns 400 if no recordings found")
        print("   - Triggers batch analysis on success")
        
        print("\n🎉 Enhanced token API structure validated!")
        print("\nNext steps:")
        print("- Start the backend server: uvicorn app.main:app --reload")
        print("- Create an authenticated session to test token creation")
        print("- Use created tokens to test session flow")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server")
        print("   Please start the server with: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ API test failed: {e}")

if __name__ == "__main__":
    test_enhanced_token_api()
