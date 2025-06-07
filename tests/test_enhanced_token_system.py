#!/usr/bin/env python3
"""
Test script for the enhanced token system.
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.database.db import SessionLocal, engine
from app.core.database.models import Token, Interview, User, CandidateSession
from app.services.interviews.verification_service import VerificationService
from app.services.interviews.session_service import SessionService

def test_enhanced_token_system():
    """Test the enhanced token system functionality."""
    print("🧪 Testing Enhanced Token System")
    print("=" * 50)
    
    # Create database session
    db = SessionLocal()
    verification_service = VerificationService()
    session_service = SessionService()
    
    try:
        # Test 1: Create a token with enhanced fields
        print("\n1. Testing enhanced token creation...")
          # Create a test user and interview if they don't exist
        test_user = db.query(User).filter(User.username == "test_interviewer").first()
        if not test_user:
            # Use a unique email to avoid conflicts
            unique_email = f"test_interviewer_{datetime.now().microsecond}@example.com"
            test_user = User(
                username=f"test_interviewer_{datetime.now().microsecond}",
                email=unique_email,
                hashed_password="fake_hash"
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
        
        test_interview = db.query(Interview).filter(
            Interview.interviewer_id == test_user.id,
            Interview.title == "Test Enhanced Interview"
        ).first()
        if not test_interview:
            test_interview = Interview(
                title="Test Enhanced Interview",
                slug=f"test-enhanced-interview-{datetime.now().microsecond}",
                interviewer_id=test_user.id
            )
            db.add(test_interview)
            db.commit()
            db.refresh(test_interview)
        
        # Create enhanced token
        expires_at = datetime.now() + timedelta(hours=72)
        enhanced_token = Token(
            interview_id=test_interview.id,
            candidate_name="John Doe",
            expires_at=expires_at,
            max_attempts=3,
            current_attempts=0
        )
        db.add(enhanced_token)
        db.commit()
        db.refresh(enhanced_token)
        
        print(f"✅ Created enhanced token: {enhanced_token.token_value}")
        print(f"   - Candidate: {enhanced_token.candidate_name}")
        print(f"   - Expires: {enhanced_token.expires_at}")
        print(f"   - Max attempts: {enhanced_token.max_attempts}")
        print(f"   - Current attempts: {enhanced_token.current_attempts}")
        
        # Test 2: Token verification
        print("\n2. Testing enhanced token verification...")
        
        verification_result = verification_service.verify_token(
            enhanced_token.token_value, db, check_used=True
        )
        
        print(f"✅ Token verification result:")
        print(f"   - Valid: {verification_result['valid']}")
        print(f"   - Status: {verification_result['status']}")
        print(f"   - Token object included: {'token_obj' in verification_result}")
        
        # Test 3: Session creation with attempt counting
        print("\n3. Testing session creation with attempt counting...")
        
        token_obj = verification_result.get('token_obj')
        if token_obj:
            session = session_service.start_session(token_obj, db)
            print(f"✅ Created session: {session.id}")
            
            # Refresh token to see updated attempt count
            db.refresh(enhanced_token)
            print(f"   - Token attempts after session: {enhanced_token.current_attempts}/{enhanced_token.max_attempts}")
            print(f"   - Token is_used: {enhanced_token.is_used}")
        
        # Test 4: Attempt limit validation
        print("\n4. Testing attempt limit validation...")
        
        # Try to create more sessions than allowed
        for attempt in range(2, 5):  # Attempts 2, 3, 4 (already used 1)
            verification_result = verification_service.verify_token(
                enhanced_token.token_value, db, check_used=False  # Don't check is_used for this test
            )
            
            if verification_result['valid'] and verification_result['status'] != 'attempts_exceeded':
                token_obj = verification_result.get('token_obj')
                try:
                    session = session_service.start_session(token_obj, db)
                    db.refresh(enhanced_token)
                    print(f"   - Attempt {attempt}: Success (total attempts: {enhanced_token.current_attempts})")
                except Exception as e:
                    print(f"   - Attempt {attempt}: Failed - {e}")
            else:
                print(f"   - Attempt {attempt}: Blocked - {verification_result['status']}")
                break
        
        # Test 5: Expiry validation  
        print("\n5. Testing token expiry validation...")
        
        # Create an expired token
        expired_token = Token(
            interview_id=test_interview.id,
            candidate_name="Jane Doe",
            expires_at=datetime.now() - timedelta(hours=1),  # Expired 1 hour ago
            max_attempts=1,
            current_attempts=0
        )
        db.add(expired_token)
        db.commit()
        
        expired_verification = verification_service.verify_token(
            expired_token.token_value, db, check_used=True
        )
        
        print(f"✅ Expired token verification:")
        print(f"   - Valid: {expired_verification['valid']}")
        print(f"   - Status: {expired_verification['status']}")
        
        print("\n🎉 Enhanced token system test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_enhanced_token_system()
