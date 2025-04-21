"""
Endpoints for managing interview questions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import db_dependency, active_user_dependency
from app.core.database.models import User, Interview, Question
from app.schemas import QuestionCreate, QuestionResponse, QuestionOrderUpdate

# Create router
questions_router = APIRouter()

@questions_router.get("/{interview_id}/questions", response_model=List[QuestionResponse])
def get_questions(
    interview_id: int,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Get all questions for an interview"""
    # Verify interview exists and belongs to user
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.owner_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    return interview.questions

@questions_router.post("/{interview_id}/questions", response_model=QuestionResponse)
def add_question(
    interview_id: int,
    question: QuestionCreate,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Add a question to an interview"""
    # Verify interview exists and belongs to user
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.owner_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Get the current highest order number
    highest_order = db.query(Question).filter(
        Question.interview_id == interview_id
    ).order_by(Question.order.desc()).first()
    
    next_order = 1
    if highest_order:
        next_order = highest_order.order + 1
    
    # Create new question
    db_question = Question(
        interview_id=interview_id,
        text=question.text,
        preparation_time=question.preparation_time,
        responding_time=question.responding_time,
        order=next_order
    )
    
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    
    return db_question

@questions_router.put("/{interview_id}/questions/{question_id}", response_model=QuestionResponse)
def update_question(
    interview_id: int,
    question_id: int,
    question_update: QuestionCreate,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Update a question in an interview"""
    # Verify interview exists and belongs to user
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.owner_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Get the question
    question = db.query(Question).filter(
        Question.id == question_id,
        Question.interview_id == interview_id
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Update question
    question.text = question_update.text
    question.preparation_time = question_update.preparation_time
    question.responding_time = question_update.responding_time
    
    db.commit()
    db.refresh(question)
    
    return question

@questions_router.delete("/{interview_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    interview_id: int,
    question_id: int,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Delete a question from an interview"""
    # Verify interview exists and belongs to user
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.owner_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Get the question
    question = db.query(Question).filter(
        Question.id == question_id,
        Question.interview_id == interview_id
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Delete question
    db.delete(question)
    db.commit()
    
    # Reorder remaining questions
    questions = db.query(Question).filter(
        Question.interview_id == interview_id
    ).order_by(Question.order).all()
    
    for i, q in enumerate(questions, start=1):
        q.order = i
    
    db.commit()
    
    return None

@questions_router.put("/{interview_id}/questions/reorder", response_model=List[QuestionResponse])
def reorder_questions(
    interview_id: int,
    order_updates: List[QuestionOrderUpdate],
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Update the order of multiple questions at once"""
    # Verify interview exists and belongs to user
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.owner_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    if not order_updates:
        raise HTTPException(status_code=400, detail="No order updates provided")
    
    # Get all questions for this interview
    question_ids = [update.question_id for update in order_updates]
    questions = db.query(Question).filter(
        Question.id.in_(question_ids),
        Question.interview_id == interview_id
    ).all()
    
    # Verify all questions exist
    if len(questions) != len(question_ids):
        raise HTTPException(status_code=404, detail="One or more questions not found")
    
    # Update question orders
    for update in order_updates:
        question = next((q for q in questions if q.id == update.question_id), None)
        if question:
            question.order = update.new_order
    
    db.commit()
    
    # Return updated questions in order
    updated_questions = db.query(Question).filter(
        Question.interview_id == interview_id
    ).order_by(Question.order).all()
    
    return updated_questions