#!/usr/bin/env python3
"""
Test script to verify API endpoints are functional after cleanup
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_endpoint_availability():
    """Test that our cleaned endpoints are available"""
    
    # Test endpoints that should be accessible without auth
    test_endpoints = [
        f"{BASE_URL}/candidates/interviews/access",
        f"{BASE_URL}/candidates/interviews/start-session", 
        f"{BASE_URL}/candidates/interviews/complete-session",
        f"{BASE_URL}/candidates/interviews/recordings"
    ]
    
    print("=== TESTING ENDPOINT AVAILABILITY ===")
    
    for endpoint in test_endpoints:
        try:
            # Use OPTIONS to check if endpoint exists
            resp = requests.options(endpoint)
            status = "✓ Available" if resp.status_code < 500 else f"✗ Error ({resp.status_code})"
            print(f"{endpoint}: {status}")
        except Exception as e:
            print(f"{endpoint}: ✗ Connection error")
    
    # Test a POST request to see proper error handling (without valid data)
    print("\n=== TESTING ERROR HANDLING ===")
    try:
        resp = requests.post(f"{BASE_URL}/candidates/interviews/access", 
                           json={"token": "invalid_test_token"})
        print(f"POST /interviews/access with invalid token: {resp.status_code} (expected 400/404)")
        
        if resp.status_code in [400, 404]:
            print("✓ Proper error handling for invalid tokens")
        else:
            print("✗ Unexpected response code")
            
    except Exception as e:
        print(f"✗ Error testing endpoint: {e}")

if __name__ == "__main__":
    test_endpoint_availability()
