# Credit System Database Models and Implementation Plan

## Overview
This document outlines the database models and implementation plan for transitioning from a traditional subscription-based interview platform to a hybrid credit system that combines subscription plans with pay-per-use credits.

## Business Model Summary
- **Hybrid Approach**: Subscription plans include monthly credits + ability to purchase additional credits
- **Credit Consumption**: 1 credit = 1 complete interview session (transcription + AI analysis)
- **Flexible Usage**: Accommodates both regular and seasonal hiring patterns
- **Transparent Pricing**: Clear credit consumption and balance tracking

## Database Schema Design

### 1. Core Credit Models

#### CreditAccount Model
```python
class CreditAccount(Base):
    __tablename__ = "credit_accounts"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Purchased credits tracking
    available_credits = Column(Integer, default=0, nullable=False)
    used_credits = Column(Integer, default=0, nullable=False)
    total_purchased = Column(Integer, default=0, nullable=False)
    
    # Subscription credits (reset monthly)
    monthly_included_credits = Column(Integer, default=0, nullable=False)
    monthly_credits_used = Column(Integer, default=0, nullable=False)
    monthly_reset_date = Column(DateTime(timezone=True), nullable=True)
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="credit_account")
    transactions = relationship("CreditTransaction", back_populates="account", cascade="all, delete-orphan")
    usage_records = relationship("CreditUsage", back_populates="account", cascade="all, delete-orphan")
    
    # Computed properties
    @property
    def total_available_credits(self):
        """Calculate total available credits (purchased + unused monthly)"""
        unused_monthly = max(0, self.monthly_included_credits - self.monthly_credits_used)
        return self.available_credits + unused_monthly
    
    @property
    def monthly_credits_remaining(self):
        """Calculate remaining monthly subscription credits"""
        return max(0, self.monthly_included_credits - self.monthly_credits_used)
```

#### CreditTransaction Model
```python
class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("credit_accounts.id"), nullable=False)
    
    # Transaction details
    transaction_type = Column(String(50), nullable=False)  # 'purchase', 'usage', 'refund', 'subscription_grant', 'admin_adjustment'
    amount = Column(Integer, nullable=False)  # Credits (positive for add, negative for use)
    balance_after = Column(Integer, nullable=False)  # Balance after this transaction
    
    # Context and metadata
    description = Column(Text, nullable=False)
    reference_id = Column(String(255), nullable=True)  # session_id, stripe_payment_id, etc.
    reference_type = Column(String(50), nullable=True)  # 'session', 'stripe_payment', 'admin', etc.
    
    # Additional metadata (JSON for flexibility)
    metadata = Column(JSON, nullable=True)  # Cost breakdown, processing details, etc.
    
    # Audit timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    account = relationship("CreditAccount", back_populates="transactions")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_credit_transaction_account_created', 'account_id', 'created_at'),
        Index('idx_credit_transaction_type', 'transaction_type'),
        Index('idx_credit_transaction_reference', 'reference_type', 'reference_id'),
    )
```

#### CreditUsage Model
```python
class CreditUsage(Base):
    __tablename__ = "credit_usage"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("credit_accounts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("candidate_sessions.id"), nullable=False)
    
    # Usage tracking
    credits_consumed = Column(Integer, default=1, nullable=False)
    cost_breakdown = Column(JSON, nullable=True)  # {"transcription": 0.3, "analysis": 0.7}
    
    # Processing details for analytics
    recordings_count = Column(Integer, nullable=True)
    total_audio_duration = Column(Integer, nullable=True)  # seconds
    analysis_complexity = Column(String(50), default='standard')  # 'basic', 'standard', 'advanced'
    processing_status = Column(String(50), default='completed')  # 'completed', 'failed', 'partial'
    
    # Performance metrics
    transcription_duration = Column(Integer, nullable=True)  # seconds
    analysis_duration = Column(Integer, nullable=True)  # seconds
    
    # Audit timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    account = relationship("CreditAccount", back_populates="usage_records")
    user = relationship("User")
    session = relationship("CandidateSession")
    
    # Indexes for performance and analytics
    __table_args__ = (
        Index('idx_credit_usage_user_created', 'user_id', 'created_at'),
        Index('idx_credit_usage_session', 'session_id'),
        Index('idx_credit_usage_account', 'account_id'),
    )
```

### 2. Enhanced Existing Models

#### User Model Enhancements
```python
class User(Base):
    # ... existing fields ...
    
    # Credit system relationship
    credit_account = relationship("CreditAccount", uselist=False, back_populates="user", cascade="all, delete-orphan")
    
    # Computed properties for credits
    @property
    def total_available_credits(self):
        """Get total available credits (subscription + purchased)"""
        if not self.credit_account:
            return 0
        return self.credit_account.total_available_credits
    
    @property
    def can_process_interview(self, required_credits: int = 1):
        """Check if user has sufficient credits for interview processing"""
        return self.total_available_credits >= required_credits
    
    @property
    def credit_balance_summary(self):
        """Get credit balance summary for API responses"""
        if not self.credit_account:
            return {
                "available_credits": 0,
                "monthly_included": 0,
                "monthly_used": 0,
                "total_available": 0
            }
        
        account = self.credit_account
        return {
            "available_credits": account.available_credits,
            "monthly_included": account.monthly_included_credits,
            "monthly_used": account.monthly_credits_used,
            "total_available": account.total_available_credits
        }
```

#### CandidateSession Model Enhancements
```python
class CandidateSession(Base):
    # ... existing fields ...
    
    # Credit tracking
    credits_consumed = Column(Integer, default=0)
    credit_usage_id = Column(Integer, ForeignKey("credit_usage.id"), nullable=True)
    
    # Processing cost tracking
    processing_cost_breakdown = Column(JSON, nullable=True)
    
    # Relationship to credit usage
    credit_usage = relationship("CreditUsage", foreign_keys=[credit_usage_id])
```

## Implementation Plan

### Phase 1: Database Schema Implementation (Week 1-2)

#### 1.1 Create Migration Scripts
```python
# Migration: Add credit system tables
def upgrade():
    # Create credit_accounts table
    op.create_table('credit_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('available_credits', sa.Integer(), nullable=False, default=0),
        sa.Column('used_credits', sa.Integer(), nullable=False, default=0),
        sa.Column('total_purchased', sa.Integer(), nullable=False, default=0),
        sa.Column('monthly_included_credits', sa.Integer(), nullable=False, default=0),
        sa.Column('monthly_credits_used', sa.Integer(), nullable=False, default=0),
        sa.Column('monthly_reset_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    
    # Create indexes
    op.create_index('idx_credit_accounts_user', 'credit_accounts', ['user_id'])
    
    # Create credit_transactions table
    # ... similar structure
    
    # Create credit_usage table
    # ... similar structure
    
    # Add credit tracking to candidate_sessions
    op.add_column('candidate_sessions', sa.Column('credits_consumed', sa.Integer(), default=0))
    op.add_column('candidate_sessions', sa.Column('credit_usage_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_session_credit_usage', 'candidate_sessions', 'credit_usage', ['credit_usage_id'], ['id'])
```

#### 1.2 Initialize Credit Accounts for Existing Users
```python
# Data migration script
def initialize_existing_user_credits():
    """Initialize credit accounts for all existing users"""
    users = db.query(User).all()
    
    for user in users:
        if not user.credit_account:
            # Create credit account
            account = CreditAccount(user_id=user.id)
            
            # Grant credits based on current subscription
            if user.subscription_plan == "starter":
                account.monthly_included_credits = 25
            elif user.subscription_plan == "professional":
                account.monthly_included_credits = 100
            elif user.subscription_plan == "enterprise":
                account.monthly_included_credits = 300
            
            # Set reset date to next billing cycle
            if user.subscription_end_date:
                account.monthly_reset_date = user.subscription_end_date
            
            db.add(account)
    
    db.commit()
```

### Phase 2: Core Services Implementation (Week 2-3)

#### 2.1 Credit Service
```python
class CreditService:
    """Core service for credit management operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_account(self, user_id: int) -> CreditAccount:
        """Get existing credit account or create new one"""
        account = self.db.query(CreditAccount).filter(CreditAccount.user_id == user_id).first()
        
        if not account:
            account = CreditAccount(user_id=user_id)
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
        
        return account
    
    def add_credits(self, user_id: int, amount: int, transaction_type: str, 
                   description: str, reference_id: str = None, metadata: dict = None) -> CreditTransaction:
        """Add credits to user account with full audit trail"""
        account = self.get_or_create_account(user_id)
        
        # Update balance based on transaction type
        if transaction_type == 'purchase':
            account.available_credits += amount
            account.total_purchased += amount
        elif transaction_type == 'subscription_grant':
            account.monthly_included_credits = amount
            account.monthly_credits_used = 0
            account.monthly_reset_date = datetime.now(timezone.utc) + timedelta(days=30)
        elif transaction_type == 'admin_adjustment':
            account.available_credits += amount
        
        # Record transaction
        transaction = CreditTransaction(
            account_id=account.id,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=account.available_credits,
            description=description,
            reference_id=reference_id,
            metadata=metadata
        )
        
        self.db.add(transaction)
        self.db.commit()
        
        logger.info(f"Added {amount} credits to user {user_id} (type: {transaction_type})")
        return transaction
    
    def consume_credits(self, user_id: int, session_id: int, amount: int = 1, 
                       cost_breakdown: dict = None, processing_details: dict = None) -> bool:
        """Consume credits for interview processing with detailed tracking"""
        account = self.get_or_create_account(user_id)
        
        # Check sufficient credits
        if account.total_available_credits < amount:
            logger.warning(f"Insufficient credits for user {user_id}: needed {amount}, available {account.total_available_credits}")
            return False
        
        # Prioritize subscription credits over purchased credits
        monthly_available = account.monthly_credits_remaining
        
        if monthly_available >= amount:
            # Use only subscription credits
            account.monthly_credits_used += amount
            credit_source = "subscription"
        else:
            # Use combination or only purchased credits
            if monthly_available > 0:
                account.monthly_credits_used = account.monthly_included_credits
                remaining = amount - monthly_available
                account.available_credits -= remaining
                credit_source = "mixed"
            else:
                account.available_credits -= amount
                credit_source = "purchased"
        
        account.used_credits += amount
        
        # Create usage record
        usage = CreditUsage(
            account_id=account.id,
            user_id=user_id,
            session_id=session_id,
            credits_consumed=amount,
            cost_breakdown=cost_breakdown,
            recordings_count=processing_details.get('recordings_count') if processing_details else None,
            total_audio_duration=processing_details.get('audio_duration') if processing_details else None,
            analysis_complexity=processing_details.get('complexity', 'standard') if processing_details else 'standard'
        )
        
        # Create transaction record
        transaction = CreditTransaction(
            account_id=account.id,
            transaction_type='usage',
            amount=-amount,
            balance_after=account.available_credits,
            description=f"Interview processing for session {session_id}",
            reference_id=str(session_id),
            reference_type='session',
            metadata={
                "credit_source": credit_source,
                "cost_breakdown": cost_breakdown,
                "processing_details": processing_details
            }
        )
        
        self.db.add_all([usage, transaction])
        self.db.commit()
        
        logger.info(f"Consumed {amount} credits for user {user_id}, session {session_id} (source: {credit_source})")
        return True
    
    def get_balance_summary(self, user_id: int) -> dict:
        """Get comprehensive credit balance summary"""
        account = self.get_or_create_account(user_id)
        
        return {
            "available_credits": account.available_credits,
            "monthly_included": account.monthly_included_credits,
            "monthly_used": account.monthly_credits_used,
            "monthly_remaining": account.monthly_credits_remaining,
            "total_available": account.total_available_credits,
            "total_purchased": account.total_purchased,
            "total_used": account.used_credits,
            "monthly_reset_date": account.monthly_reset_date.isoformat() if account.monthly_reset_date else None
        }
    
    def get_usage_history(self, user_id: int, limit: int = 50) -> List[CreditUsage]:
        """Get credit usage history for user"""
        account = self.get_or_create_account(user_id)
        
        return (self.db.query(CreditUsage)
                .filter(CreditUsage.account_id == account.id)
                .order_by(CreditUsage.created_at.desc())
                .limit(limit)
                .all())
    
    def reset_monthly_credits(self, user_id: int, new_monthly_amount: int):
        """Reset monthly subscription credits (called on subscription renewal)"""
        account = self.get_or_create_account(user_id)
        
        old_amount = account.monthly_included_credits
        account.monthly_included_credits = new_monthly_amount
        account.monthly_credits_used = 0
        account.monthly_reset_date = datetime.now(timezone.utc) + timedelta(days=30)
        
        # Record the reset as a transaction
        transaction = CreditTransaction(
            account_id=account.id,
            transaction_type='subscription_reset',
            amount=new_monthly_amount,
            balance_after=account.available_credits,
            description=f"Monthly credit reset: {old_amount} → {new_monthly_amount}",
            reference_type='subscription_renewal'
        )
        
        self.db.add(transaction)
        self.db.commit()
        
        logger.info(f"Reset monthly credits for user {user_id}: {old_amount} → {new_monthly_amount}")
```

### Phase 3: API Integration (Week 3-4)

#### 3.1 Session Completion with Credit Validation
```python
@router.patch("/interviews/complete-session")
def complete_session(
    session_data: CandidateTokenBase,
    background_tasks: BackgroundTasks,
    db: Session = db_dependency,
    session_service: SessionService = session_service_dependency
):
    """Complete session with credit consumption validation"""
    
    # Get session and validate
    session = session_service.get_session_by_token(session_data.token, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if recordings exist
    recording_count = db.query(Recording).filter(Recording.session_id == session.id).count()
    
    if recording_count == 0:
        # Mark session as incomplete - no credit consumption
        session.end_time = datetime.utcnow()
        session.status = "incomplete_no_recordings"
        db.commit()
        
        return {
            "message": "Session ended without recordings. No credits consumed.",
            "status": "incomplete",
            "recordings_required": True,
            "can_retry": True
        }
    
    # Get interview owner for credit billing
    token = db.query(Token).filter(Token.token_value == session_data.token).first()
    interview = db.query(Interview).filter(Interview.id == token.interview_id).first()
    user = interview.interviewer
    
    # Initialize credit service
    credit_service = CreditService(db)
    
    # Check credit availability
    if not credit_service.get_or_create_account(user.id).total_available_credits >= 1:
        balance = credit_service.get_balance_summary(user.id)
        raise HTTPException(
            status_code=402,  # Payment Required
            detail={
                "error": "insufficient_credits",
                "message": "Insufficient credits to process this interview. Please purchase more credits or upgrade your subscription.",
                "balance": balance,
                "required_credits": 1
            }
        )
    
    # Calculate processing details for cost tracking
    recordings = db.query(Recording).filter(Recording.session_id == session.id).all()
    total_duration = sum(getattr(r, 'duration', 0) or 0 for r in recordings)
    
    processing_details = {
        "recordings_count": len(recordings),
        "audio_duration": total_duration,
        "complexity": "advanced" if len(recordings) > 5 else "standard"
    }
    
    cost_breakdown = {
        "transcription": 0.3,
        "analysis": 0.7
    }
    
    # Consume credits
    success = credit_service.consume_credits(
        user_id=user.id,
        session_id=session.id,
        amount=1,
        cost_breakdown=cost_breakdown,
        processing_details=processing_details
    )
    
    if not success:
        raise HTTPException(
            status_code=402, 
            detail="Failed to process credit payment. Please try again."
        )
    
    # Mark session for processing
    session.credits_consumed = 1
    db.commit()
    
    # Continue with normal session completion
    session_service.complete_session_by_token(session_data.token, db, background_tasks)
    
    # Get updated balance
    updated_balance = credit_service.get_balance_summary(user.id)
    
    return {
        "message": "Session completed successfully. Interview processing initiated.",
        "status": "completed",
        "credits_consumed": 1,
        "cost_breakdown": cost_breakdown,
        "balance": updated_balance
    }
```

#### 3.2 Credit Management Endpoints
```python
@router.get("/billing/credits/balance")
def get_credit_balance(
    current_user: User = active_user_dependency,
    db: Session = db_dependency
):
    """Get comprehensive credit balance information"""
    credit_service = CreditService(db)
    balance = credit_service.get_balance_summary(current_user.id)
    
    # Add usage trends
    recent_usage = credit_service.get_usage_history(current_user.id, limit=10)
    
    return {
        "balance": balance,
        "recent_usage": recent_usage,
        "subscription_plan": current_user.subscription_plan,
        "next_reset_date": balance.get("monthly_reset_date")
    }

@router.get("/billing/credits/packages")
def get_credit_packages():
    """Get available credit packages for purchase"""
    return {
        "packages": CREDIT_PACKAGES,
        "subscription_plans": CREDIT_SUBSCRIPTION_PLANS
    }

@router.post("/billing/checkout/credits/{package_id}")
def purchase_credits(
    package_id: str,
    current_user: User = active_user_dependency,
    db: Session = db_dependency
):
    """Initiate credit package purchase"""
    if package_id not in CREDIT_PACKAGES:
        raise HTTPException(status_code=404, detail="Credit package not found")
    
    package = CREDIT_PACKAGES[package_id]
    
    # Create Stripe checkout session
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": package["stripe_price_id"],
            "quantity": 1,
        }],
        mode="payment",
        success_url=f"{settings.FRONTEND_URL}/billing/credits/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.FRONTEND_URL}/billing/credits/cancel",
        customer_email=current_user.email,
        metadata={
            "user_id": current_user.id,
            "package_id": package_id,
            "credits": package["credits"],
            "action": "purchase_credits"
        }
    )
    
    return {
        "checkout_url": checkout_session.url,
        "session_id": checkout_session.id
    }
```

### Phase 4: Migration and Testing (Week 4-5)

#### 4.1 Data Migration Strategy
1. **Initialize credit accounts** for all existing users
2. **Convert subscription limits** to monthly included credits
3. **Preserve existing data** and add credit tracking
4. **Validate credit calculations** against current usage

#### 4.2 Testing Strategy
1. **Unit tests** for credit service operations
2. **Integration tests** for API endpoints
3. **Load testing** for high-volume credit operations
4. **Migration testing** with production data copies

## Benefits Summary

### Business Benefits
- **Increased Revenue**: Higher usage customers pay proportionally more
- **Reduced Churn**: Credits provide more flexibility than hard limits
- **Better Analytics**: Detailed usage tracking and cost analysis
- **Scalable Pricing**: Easy to adjust credit costs and packages

### Customer Benefits
- **Cost Transparency**: Clear understanding of usage costs
- **Flexibility**: Handle seasonal hiring variations
- **No Waste**: Credits don't expire immediately
- **Predictable Costs**: Subscription base + usage overages

This implementation provides a robust foundation for transitioning to a credit-based billing system while maintaining backward compatibility and providing enhanced value to both the business and customers.