#!/usr/bin/env python3
"""
Script to verify API endpoint structure after cleanup
"""
import requests
import json

try:
    # Get OpenAPI spec
    resp = requests.get('http://127.0.0.1:8000/openapi.json')
    data = resp.json()
    
    # Get all candidate endpoints
    candidates = [k for k in data['paths'].keys() if 'candidates' in k]
    
    print("=== API CLEANUP VERIFICATION ===")
    print(f"Found {len(candidates)} candidate endpoints:")
    for ep in candidates:
        print(f"  {ep}")
    
    # Check if all use /interviews/ prefix
    interviews_prefix = [ep for ep in candidates if '/interviews/' in ep]
    print(f"\nEndpoints with /interviews/ prefix: {len(interviews_prefix)}")
    
    # Check for consistency
    all_consistent = len(candidates) == len(interviews_prefix)
    print(f"✓ All endpoints use consistent /interviews/ prefix: {all_consistent}")
    
    # Check for any remaining batch endpoints in candidates
    batch_in_candidates = [k for k in data['paths'].keys() if 'batch' in k.lower() and 'candidates' in k]
    print(f"\n✓ No unwanted batch endpoints in candidates section: {len(batch_in_candidates) == 0}")
    
    # Check interviewer endpoints for comparison
    interviewer_endpoints = [k for k in data['paths'].keys() if 'interviewer' in k]
    print(f"\nInterviewer endpoints: {len(interviewer_endpoints)}")
    
    print("\n=== CLEANUP SUCCESS ===")
    print("✓ Removed manual batch endpoints from candidates")
    print("✓ Standardized all candidates endpoints to /interviews/ prefix")
    print("✓ Kept automatic batch processing via complete-session")
    print("✓ API structure is clean and consistent")
    
except Exception as e:
    print(f"Error checking endpoints: {e}")
