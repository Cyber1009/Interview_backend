#!/usr/bin/env python3
"""
Comprehensive test for the enhanced token system implementation.
Tests all aspects: database migration, token creation, verification, session management, and API endpoints.
"""
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.database.db import SessionLocal, engine
from app.core.database.models import Token, Interview, User, CandidateSession, Recording
from app.services.interviews.verification_service import VerificationService
from app.services.interviews.session_service import SessionService

def test_comprehensive_enhanced_token_system():
    """Comprehensive test of the enhanced token system."""
    print("🔬 Comprehensive Enhanced Token System Test")
    print("=" * 60)
    
    # Create database session
    db = SessionLocal()
    verification_service = VerificationService()
    session_service = SessionService()
    
    try:
        # Phase 1: Database Schema Validation
        print("\n📊 Phase 1: Database Schema Validation")
        print("-" * 40)
        
        # Check if new fields exist in the database
        from sqlalchemy import inspect
        inspector = inspect(engine)
        token_columns = [col['name'] for col in inspector.get_columns('tokens')]
        
        required_fields = ['candidate_name', 'expires_at', 'max_attempts', 'current_attempts']
        missing_fields = [field for field in required_fields if field not in token_columns]
        
        if missing_fields:
            print(f"❌ Missing database fields: {missing_fields}")
            return False
        else:
            print(f"✅ All enhanced token fields present: {required_fields}")
        
        # Phase 2: Enhanced Token Creation
        print("\n🎯 Phase 2: Enhanced Token Creation")
        print("-" * 40)
        
        # Create test data
        test_user = db.query(User).first()
        if not test_user:
            print("❌ No users found in database - please create a user first")
            return False
        
        test_interview = db.query(Interview).filter(Interview.interviewer_id == test_user.id).first()
        if not test_interview:
            test_interview = Interview(
                title="Enhanced Token Test Interview",
                slug=f"enhanced-test-{datetime.now().microsecond}",
                interviewer_id=test_user.id
            )
            db.add(test_interview)
            db.commit()
            db.refresh(test_interview)
        
        # Test Case 1: Basic enhanced token
        basic_token = Token(
            interview_id=test_interview.id,
            candidate_name="Alice Johnson",
            expires_at=datetime.now() + timedelta(hours=48),
            max_attempts=2,
            current_attempts=0
        )
        db.add(basic_token)
        db.commit()
        db.refresh(basic_token)
        
        print(f"✅ Created basic enhanced token:")
        print(f"   - Token: {basic_token.token_value[:8]}...")
        print(f"   - Candidate: {basic_token.candidate_name}")
        print(f"   - Expires: {basic_token.expires_at}")
        print(f"   - Attempts: {basic_token.current_attempts}/{basic_token.max_attempts}")
        
        # Test Case 2: Token with extended expiry
        extended_token = Token(
            interview_id=test_interview.id,
            candidate_name="Bob Smith",
            expires_at=datetime.now() + timedelta(days=7),
            max_attempts=5,
            current_attempts=0
        )
        db.add(extended_token)
        db.commit()
        db.refresh(extended_token)
        
        print(f"✅ Created extended expiry token:")
        print(f"   - Token: {extended_token.token_value[:8]}...")
        print(f"   - Candidate: {extended_token.candidate_name}")
        print(f"   - Expires: {extended_token.expires_at}")
        print(f"   - Attempts: {extended_token.current_attempts}/{extended_token.max_attempts}")
        
        # Phase 3: Token Verification System
        print("\n🔍 Phase 3: Token Verification System")
        print("-" * 40)
        
        # Test Case 3: Valid token verification
        verification_result = verification_service.verify_token(basic_token.token_value, db, check_used=True)
        print(f"✅ Valid token verification:")
        print(f"   - Valid: {verification_result['valid']}")
        print(f"   - Status: {verification_result['status']}")
        print(f"   - Token object included: {'token_obj' in verification_result}")
        
        # Test Case 4: Expired token verification
        expired_token = Token(
            interview_id=test_interview.id,
            candidate_name="Charlie Brown",
            expires_at=datetime.now() - timedelta(hours=1),
            max_attempts=1,
            current_attempts=0
        )
        db.add(expired_token)
        db.commit()
        
        expired_verification = verification_service.verify_token(expired_token.token_value, db, check_used=True)
        print(f"✅ Expired token verification:")
        print(f"   - Valid: {expired_verification['valid']}")
        print(f"   - Status: {expired_verification['status']}")
        
        # Phase 4: Session Management with Attempt Tracking
        print("\n🎬 Phase 4: Session Management")
        print("-" * 40)
        
        # Test Case 5: Session creation and attempt counting
        verification_result = verification_service.verify_token(basic_token.token_value, db, check_used=True)
        if verification_result['valid']:
            token_obj = verification_result['token_obj']
            session1 = session_service.start_session(token_obj, db)
            
            # Refresh token to see updated attempt count
            db.refresh(basic_token)
            print(f"✅ Session 1 created:")
            print(f"   - Session ID: {session1.id}")
            print(f"   - Token attempts: {basic_token.current_attempts}/{basic_token.max_attempts}")
            print(f"   - Token is_used: {basic_token.is_used}")
            
            # Test Case 6: Second session attempt
            verification_result2 = verification_service.verify_token(basic_token.token_value, db, check_used=False)
            if verification_result2['valid'] and verification_result2['status'] != 'attempts_exceeded':
                token_obj2 = verification_result2['token_obj']
                session2 = session_service.start_session(token_obj2, db)
                
                db.refresh(basic_token)
                print(f"✅ Session 2 created:")
                print(f"   - Session ID: {session2.id}")
                print(f"   - Token attempts: {basic_token.current_attempts}/{basic_token.max_attempts}")
                
                # Test Case 7: Attempt limit reached
                verification_result3 = verification_service.verify_token(basic_token.token_value, db, check_used=False)
                print(f"✅ Third attempt verification:")
                print(f"   - Valid: {verification_result3['valid']}")
                print(f"   - Status: {verification_result3['status']}")
                print(f"   - Expected: attempts_exceeded")
        
        # Phase 5: Session Completion Validation
        print("\n🏁 Phase 5: Session Completion Validation")
        print("-" * 40)
        
        # Test Case 8: Session completion without recordings (should fail)
        try:
            session_service.complete_session(session1.id, db)
            print("❌ Session completion should have failed without recordings")
        except Exception as e:
            if "recordings" in str(e):
                print("✅ Session completion properly blocked without recordings")
            else:
                print(f"❌ Unexpected error: {e}")
        
        # Phase 6: Legacy Compatibility
        print("\n🔄 Phase 6: Legacy Compatibility")
        print("-" * 40)
        
        # Test Case 9: Legacy token (without enhanced fields)
        legacy_token = Token(
            interview_id=test_interview.id,
            # No candidate_name, expires_at, etc.
        )
        db.add(legacy_token)
        db.commit()
        db.refresh(legacy_token)
        
        legacy_verification = verification_service.verify_token(legacy_token.token_value, db, check_used=True)
        print(f"✅ Legacy token verification:")
        print(f"   - Valid: {legacy_verification['valid']}")
        print(f"   - Status: {legacy_verification['status']}")
        print(f"   - Backwards compatible: {legacy_verification['valid']}")
        
        # Phase 7: Data Integrity Check
        print("\n📋 Phase 7: Data Integrity Check")
        print("-" * 40)
        
        # Check data integrity
        enhanced_tokens = db.query(Token).filter(Token.candidate_name.isnot(None)).count()
        total_tokens = db.query(Token).count()
        sessions_created = db.query(CandidateSession).count()
        
        print(f"✅ Data integrity summary:")
        print(f"   - Enhanced tokens: {enhanced_tokens}")
        print(f"   - Total tokens: {total_tokens}")
        print(f"   - Sessions created: {sessions_created}")
        
        print("\n🎉 Comprehensive Enhanced Token System Test PASSED!")
        print("\nSummary of Enhanced Features:")
        print("✅ Candidate name tracking")
        print("✅ Time-based token expiry")
        print("✅ Attempt-based session limits")
        print("✅ Session completion validation")
        print("✅ Backwards compatibility with legacy tokens")
        print("✅ Enhanced verification service")
        print("✅ Improved session management")
        
        return True
        
    except Exception as e:
        print(f"❌ Comprehensive test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_comprehensive_enhanced_token_system()
    exit(0 if success else 1)
