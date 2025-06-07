# Credit System Implementation Plan

## Phase 1: Database Schema Updates

### New Models to Add:

```python
class CreditAccount(Base):
    __tablename__ = "credit_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Credit balance tracking
    available_credits = Column(Integer, default=0)
    used_credits = Column(Integer, default=0)
    total_purchased = Column(Integer, default=0)
    
    # Subscription credits (reset monthly)
    monthly_included_credits = Column(Integer, default=0)
    monthly_credits_used = Column(Integer, default=0)
    monthly_reset_date = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="credit_account")
    transactions = relationship("CreditTransaction", back_populates="account")

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("credit_accounts.id"))
    
    # Transaction details
    transaction_type = Column(String)  # 'purchase', 'usage', 'refund', 'subscription_grant'
    amount = Column(Integer)  # Credits (positive for add, negative for use)
    balance_after = Column(Integer)  # Balance after this transaction
    
    # Context
    description = Column(String)
    reference_id = Column(String, nullable=True)  # session_id, payment_id, etc.
    reference_type = Column(String, nullable=True)  # 'session', 'purchase', etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    account = relationship("CreditAccount", back_populates="transactions")

class CreditUsage(Base):
    __tablename__ = "credit_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(Integer, ForeignKey("candidate_sessions.id"))
    
    # Usage tracking
    credits_consumed = Column(Integer, default=1)
    cost_breakdown = Column(JSON)  # {"transcription": 0.3, "analysis": 0.7}
    
    # Processing details
    recordings_count = Column(Integer)
    total_audio_duration = Column(Integer)  # seconds
    analysis_complexity = Column(String)  # 'basic', 'advanced', 'comprehensive'
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    session = relationship("CandidateSession")
```

### Updates to Existing Models:

```python
# Add to User model
class User(Base):
    # ... existing fields ...
    
    # Credit system fields
    credit_account = relationship("CreditAccount", uselist=False, back_populates="user")
    
    @property
    def total_available_credits(self):
        """Get total available credits (subscription + purchased)"""
        if not self.credit_account:
            return 0
        return (self.credit_account.available_credits + 
                max(0, self.credit_account.monthly_included_credits - 
                    self.credit_account.monthly_credits_used))
    
    @property
    def can_process_interview(self):
        """Check if user has credits to process an interview"""
        return self.total_available_credits >= 1
```

## Phase 2: Credit Management Services

### Core Credit Service:

```python
class CreditService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def initialize_account(self, user_id: int) -> CreditAccount:
        """Initialize credit account for new user"""
        account = CreditAccount(user_id=user_id)
        self.db.add(account)
        self.db.commit()
        return account
    
    def add_credits(self, user_id: int, amount: int, transaction_type: str, 
                   description: str, reference_id: str = None) -> CreditTransaction:
        """Add credits to user account"""
        account = self.get_or_create_account(user_id)
        
        # Update balance
        account.available_credits += amount
        account.total_purchased += amount if transaction_type == 'purchase' else 0
        
        # Record transaction
        transaction = CreditTransaction(
            account_id=account.id,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=account.available_credits,
            description=description,
            reference_id=reference_id
        )
        
        self.db.add(transaction)
        self.db.commit()
        return transaction
    
    def consume_credits(self, user_id: int, amount: int, session_id: int, 
                       cost_breakdown: dict = None) -> bool:
        """Consume credits for interview processing"""
        account = self.get_or_create_account(user_id)
        
        # Check if sufficient credits available
        if not self.has_sufficient_credits(user_id, amount):
            return False
        
        # Prioritize using subscription credits first
        monthly_available = (account.monthly_included_credits - 
                           account.monthly_credits_used)
        
        if monthly_available >= amount:
            # Use subscription credits
            account.monthly_credits_used += amount
        else:
            # Use combination of subscription and purchased credits
            if monthly_available > 0:
                account.monthly_credits_used = account.monthly_included_credits
                remaining = amount - monthly_available
                account.available_credits -= remaining
            else:
                # Use only purchased credits
                account.available_credits -= amount
        
        # Record usage
        usage = CreditUsage(
            user_id=user_id,
            session_id=session_id,
            credits_consumed=amount,
            cost_breakdown=cost_breakdown
        )
        
        # Record transaction
        transaction = CreditTransaction(
            account_id=account.id,
            transaction_type='usage',
            amount=-amount,
            balance_after=account.available_credits,
            description=f"Interview processing for session {session_id}",
            reference_id=str(session_id),
            reference_type='session'
        )
        
        self.db.add_all([usage, transaction])
        self.db.commit()
        return True
    
    def has_sufficient_credits(self, user_id: int, required: int) -> bool:
        """Check if user has sufficient credits"""
        account = self.get_or_create_account(user_id)
        total_available = (account.available_credits + 
                          max(0, account.monthly_included_credits - 
                              account.monthly_credits_used))
        return total_available >= required
    
    def reset_monthly_credits(self, user_id: int, new_monthly_amount: int):
        """Reset monthly subscription credits (called on subscription renewal)"""
        account = self.get_or_create_account(user_id)
        account.monthly_included_credits = new_monthly_amount
        account.monthly_credits_used = 0
        account.monthly_reset_date = datetime.now(timezone.utc) + timedelta(days=30)
        self.db.commit()
```

## Phase 3: Updated Subscription Plans

### New Subscription Configuration:

```python
CREDIT_SUBSCRIPTION_PLANS = {
    "starter": {
        "name": "Starter Plan",
        "price_id": settings.STRIPE_STARTER_PRICE_ID,
        "monthly_price": 29.00,
        "duration_days": 30,
        "included_credits": 25,
        "credit_overage_price": 1.50,
        "features": [
            "25 interview credits per month",
            "3 interview templates",
            "Basic analytics",
            "Email support",
            "Additional credits: $1.50 each"
        ]
    },
    "professional": {
        "name": "Professional Plan", 
        "price_id": settings.STRIPE_PROFESSIONAL_PRICE_ID,
        "monthly_price": 79.00,
        "duration_days": 30,
        "included_credits": 100,
        "credit_overage_price": 1.00,
        "features": [
            "100 interview credits per month",
            "10 interview templates",
            "Advanced analytics and exports",
            "Priority support",
            "Additional credits: $1.00 each"
        ]
    },
    "enterprise": {
        "name": "Enterprise Plan",
        "price_id": settings.STRIPE_ENTERPRISE_PRICE_ID,
        "monthly_price": 199.00,
        "duration_days": 30,
        "included_credits": 300,
        "credit_overage_price": 0.75,
        "features": [
            "300 interview credits per month", 
            "Unlimited interview templates",
            "Full analytics suite",
            "Dedicated support",
            "API access",
            "Additional credits: $0.75 each"
        ]
    }
}

# Pay-as-you-go credit packages
CREDIT_PACKAGES = {
    "small": {
        "name": "Small Credit Package",
        "credits": 10,
        "price": 25.00,
        "price_per_credit": 2.50,
        "stripe_price_id": settings.STRIPE_CREDITS_SMALL_PRICE_ID
    },
    "medium": {
        "name": "Medium Credit Package", 
        "credits": 50,
        "price": 100.00,
        "price_per_credit": 2.00,
        "stripe_price_id": settings.STRIPE_CREDITS_MEDIUM_PRICE_ID
    },
    "large": {
        "name": "Large Credit Package",
        "credits": 100, 
        "price": 175.00,
        "price_per_credit": 1.75,
        "stripe_price_id": settings.STRIPE_CREDITS_LARGE_PRICE_ID
    },
    "bulk": {
        "name": "Bulk Credit Package",
        "credits": 500,
        "price": 750.00,
        "price_per_credit": 1.50,
        "stripe_price_id": settings.STRIPE_CREDITS_BULK_PRICE_ID
    }
}
```

## Phase 4: API Endpoint Updates

### New Credit Management Endpoints:

```python
@router.get("/credits/balance", response_model=CreditBalanceResponse)
def get_credit_balance(
    current_user: User = active_user_dependency,
    db: Session = db_dependency
):
    """Get current credit balance and usage"""
    credit_service = CreditService(db)
    account = credit_service.get_or_create_account(current_user.id)
    
    return CreditBalanceResponse(
        available_credits=account.available_credits,
        monthly_included=account.monthly_included_credits,
        monthly_used=account.monthly_credits_used,
        total_available=current_user.total_available_credits,
        usage_history=account.transactions[-10:]  # Last 10 transactions
    )

@router.post("/credits/purchase/{package_id}", response_model=CheckoutSession)
def purchase_credits(
    package_id: str,
    current_user: User = active_user_dependency,
    db: Session = db_dependency
):
    """Purchase additional credits"""
    if package_id not in CREDIT_PACKAGES:
        not_found("Credit Package", package_id)
    
    package = CREDIT_PACKAGES[package_id]
    
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": package["stripe_price_id"],
            "quantity": 1,
        }],
        mode="payment",  # One-time payment for credits
        success_url=f"{settings.FRONTEND_URL}/credits/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.FRONTEND_URL}/credits/cancel",
        customer_email=current_user.email,
        metadata={
            "user_id": current_user.id,
            "package_id": package_id,
            "credits": package["credits"],
            "action": "purchase_credits"
        }
    )
    
    return CheckoutSession(
        checkout_url=checkout_session.url,
        session_id=checkout_session.id
    )

@router.get("/credits/usage", response_model=List[CreditUsageResponse])
def get_credit_usage_history(
    limit: int = Query(50, le=100),
    current_user: User = active_user_dependency,
    db: Session = db_dependency
):
    """Get credit usage history"""
    usage_records = (db.query(CreditUsage)
                    .filter(CreditUsage.user_id == current_user.id)
                    .order_by(CreditUsage.created_at.desc())
                    .limit(limit)
                    .all())
    
    return usage_records
```

### Updated Session Completion with Credit Check:

```python
@router.patch("/interviews/complete-session")
def complete_session(
    session_data: CandidateTokenBase,
    background_tasks: BackgroundTasks,
    db: Session = db_dependency,
    session_service: SessionService = session_service_dependency
):
    """Complete session with credit consumption"""
    
    # Get session and user
    token = db.query(Token).filter(Token.token_value == session_data.token).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    session = db.query(CandidateSession).filter(CandidateSession.token_id == token.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get interview owner (who will be charged)
    interview = db.query(Interview).filter(Interview.id == token.interview_id).first()
    user = interview.interviewer
    
    # Check credit availability
    credit_service = CreditService(db)
    if not credit_service.has_sufficient_credits(user.id, 1):
        raise HTTPException(
            status_code=402,  # Payment Required
            detail={
                "error": "insufficient_credits",
                "message": "Insufficient credits to process this interview. Please purchase more credits or upgrade your subscription.",
                "available_credits": user.total_available_credits,
                "required_credits": 1
            }
        )
    
    # Record credit consumption
    cost_breakdown = {
        "transcription": 0.3,
        "analysis": 0.7
    }
    
    success = credit_service.consume_credits(
        user_id=user.id,
        amount=1,
        session_id=session.id,
        cost_breakdown=cost_breakdown
    )
    
    if not success:
        raise HTTPException(status_code=402, detail="Failed to process credit payment")
    
    # Continue with session completion
    session_service.complete_session_by_token(session_data.token, db, background_tasks)
    
    return {
        "message": "Session completed successfully",
        "credits_consumed": 1,
        "remaining_credits": user.total_available_credits - 1
    }
```

## Phase 5: Webhook Updates for Credit Processing

### Enhanced Stripe Webhook for Credit Purchases:

```python
async def handle_credit_purchase_completion(db: Session, checkout_session):
    """Handle completed credit package purchases"""
    
    metadata = getattr(checkout_session, 'metadata', {})
    user_id = metadata.get("user_id")
    package_id = metadata.get("package_id")
    credits = int(metadata.get("credits", 0))
    
    if not all([user_id, package_id, credits]):
        logger.error("Missing metadata for credit purchase")
        return
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"User {user_id} not found for credit purchase")
        return
    
    # Add credits to account
    credit_service = CreditService(db)
    transaction = credit_service.add_credits(
        user_id=int(user_id),
        amount=credits,
        transaction_type='purchase',
        description=f"Purchased {credits} credits ({package_id} package)",
        reference_id=checkout_session.id
    )
    
    logger.info(f"Added {credits} credits to user {user_id}")
    
    # Send confirmation email
    # TODO: Implement email notification
```

## Business Benefits

### **For Your Business:**
1. **Predictable Revenue**: Subscription base provides steady income
2. **Usage-Based Scaling**: High-volume users pay proportionally more
3. **Reduced Churn**: Credits don't expire, reducing pressure on customers
4. **Upsell Opportunities**: Easy to upgrade plans or purchase additional credits
5. **Transparent Pricing**: Customers understand exactly what they're paying for

### **For Your Customers:**
1. **Cost Control**: Pay only for what they use beyond included credits
2. **Flexibility**: Can handle seasonal variations in hiring
3. **Transparent Billing**: Clear credit consumption tracking
4. **No Waste**: Unused subscription credits roll over (with limits)
5. **Scalability**: Can easily increase usage without changing plans

## Migration Strategy

### **For Existing Customers:**
1. **Grandfathering**: Honor current subscription terms until renewal
2. **Credit Grant**: Convert current "candidate limits" to equivalent credits
3. **Communication**: 60-day advance notice with clear benefit explanation
4. **Incentives**: Offer bonus credits for early adopters

### **Implementation Timeline:**
- **Week 1-2**: Database schema updates and core credit service
- **Week 3-4**: API endpoint updates and testing
- **Week 5-6**: Frontend integration and webhook updates
- **Week 7-8**: Testing and migration scripts
- **Week 9-10**: Phased rollout and customer communication

This credit system provides the flexibility and transparency that modern SaaS customers expect while maintaining predictable revenue for your business.
