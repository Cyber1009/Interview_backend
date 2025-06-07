"""
Background tasks and scheduled jobs for the application.
"""
from datetime import datetime, timedelta
import os
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import BackgroundTasks

from app.core.database.db import SessionLocal
from app.core.database.models import (
    User, PendingAccount, Recording, Token
)
from app.core.config import settings
from app.services.recordings.recording_service import RecordingService

# Configure logging
logger = logging.getLogger(__name__)

# Create scheduler
scheduler = AsyncIOScheduler()

# Services
recording_service = RecordingService()

# Store for background tasks
background_tasks = BackgroundTasks()

# --- JOBS ---

def subscription_sync_job():
    """
    Check and update subscription status based on end dates.
    
    This job runs daily and:
    1. Deactivates accounts with expired subscriptions
    2. Updates subscription status fields accordingly
    """
    try:
        db = SessionLocal()
        now = datetime.now()
        
        # Find users with expired subscriptions that are still active
        expired_users = (
            db.query(User)
            .filter(User.subscription_end_date < now)
            .filter(User.is_active == True)
            .all()
        )
        
        for user in expired_users:
            user.is_active = False
            user.subscription_status = "expired"
            logger.info(f"Deactivated expired subscription for user: {user.username}")
        
        # Find users whose subscriptions will expire soon (in next 7 days)
        expiring_soon = (
            db.query(User)
            .filter(User.subscription_end_date > now)
            .filter(User.subscription_end_date < now + timedelta(days=7))
            .filter(User.is_active == True)
            .all()
        )
        
        # Log upcoming expirations (in production, you might want to send emails)
        for user in expiring_soon:
            days_left = (user.subscription_end_date - now).days
            logger.info(f"Subscription expiring soon for {user.username}: {days_left} days left")
        
        db.commit()
        logger.info(f"Subscription sync completed. Deactivated {len(expired_users)} expired accounts.")
    except Exception as e:
        logger.error(f"Error in subscription sync job: {str(e)}")
    finally:
        db.close()

def cleanup_pending_accounts_job():
    """Remove pending accounts that have expired verification tokens."""
    db = SessionLocal()
    try:
        now = datetime.now()
        
        # Find pending accounts where the verification token has expired
        expired_pending_accounts = (
            db.query(PendingAccount)
            .filter(PendingAccount.expiration_date < now)
            .all()
        )
        
        # Delete expired pending accounts
        for account in expired_pending_accounts:
            db.delete(account)
        
        db.commit()
        logger.info(f"Removed {len(expired_pending_accounts)} expired pending account(s)")
    except Exception as e:
        logger.error(f"Error cleaning up pending accounts: {str(e)}")
    finally:
        db.close()

def cleanup_expired_tokens_job():
    """Remove old or unused tokens based on creation date."""
    db = SessionLocal()
    try:
        # Consider unused tokens older than 7 days as expired
        unused_expiration_cutoff = datetime.now() - timedelta(days=7)
        # Used tokens can stay longer (30 days)
        used_expiration_cutoff = datetime.now() - timedelta(days=30)
        
        # Find expired tokens
        expired_tokens = (
            db.query(Token)
            .filter(
                # Unused tokens older than 7 days
                ((Token.is_used == False) & (Token.created_at < unused_expiration_cutoff)) |
                # OR used tokens older than 30 days
                ((Token.is_used == True) & (Token.created_at < used_expiration_cutoff))
            )
            .all()
        )
        
        # Delete expired tokens
        for token in expired_tokens:
            db.delete(token)
        
        db.commit()
        logger.info(f"Removed {len(expired_tokens)} old/expired token(s)")
    except Exception as e:
        logger.error(f"Error cleaning up expired tokens: {str(e)}")
    finally:
        db.close()

def cleanup_old_recordings_job():
    """Clean up old recordings based on retention policy."""
    db = SessionLocal()
    try:
        now = datetime.now()
        failed_cutoff = now - timedelta(days=7)
        old_cutoff = now - timedelta(days=30)
        deleted_count = 0
        
        # Find recordings to clean up
        old_recordings = db.query(Recording).filter(
            (
                (Recording.transcription_status == "failed") &
                (Recording.created_at < failed_cutoff)
            ) |
            (
                (Recording.created_at < old_cutoff) &
                (Recording.transcription_status == "skipped")
            )
        ).all()
        
        for recording in old_recordings:
            # Delete the physical file if it exists
            if recording.file_path and os.path.exists(recording.file_path):
                try:
                    os.remove(recording.file_path)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting file {recording.file_path}: {str(e)}")
            
            # Update the database record to mark file as removed
            recording.file_path = None
            recording.file_removed_at = now
        
        if old_recordings:
            db.commit()
            logger.info(f"Removed {deleted_count} old recording files")
        else:
            logger.info("No old recording files to remove")
    except Exception as e:
        logger.error(f"Error cleaning up old recordings: {str(e)}")
    finally:
        db.close()

async def process_transcription_retries_job():
    """
    Check for recordings with scheduled retries and process them.
    This job runs every 5 minutes to retry failed transcriptions.
    """
    try:
        logger.info("Running transcription retry job")
        count = await recording_service.process_pending_retries(background_tasks)
        if count > 0:
            logger.info(f"Queued {count} recording(s) for transcription retry")
        else:
            logger.debug("No recordings found for transcription retry")
    except Exception as e:
        logger.error(f"Error in transcription retry job: {str(e)}")

# --- SCHEDULER INTERFACE ---

def setup_scheduler():
    """Initialize and start the task scheduler."""
    return start_scheduler()

def shutdown_scheduler():
    """Shut down the task scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Task scheduler shut down successfully")
    return True

# --- SCHEDULER SETUP ---

def start_scheduler():
    """Initialize and start the task scheduler with all configured jobs."""
    # Subscription sync job - runs daily at midnight
    scheduler.add_job(
        subscription_sync_job,
        'cron', 
        hour=0,
        minute=0,
        id="subscription_sync_job"
    )
    
    # Cleanup pending accounts - run daily
    scheduler.add_job(
        cleanup_pending_accounts_job,
        'cron',
        hour=1,
        minute=0,
        id="cleanup_pending_accounts_job"
    )
    
    # Cleanup expired tokens - run daily
    scheduler.add_job(
        cleanup_expired_tokens_job,
        'cron',
        hour=2,
        minute=0,
        id="cleanup_expired_tokens_job"
    )
    
    # Cleanup old recordings - run weekly on Sunday
    scheduler.add_job(
        cleanup_old_recordings_job,
        'cron',
        day_of_week='sun',
        hour=3,
        minute=0,
        id="cleanup_old_recordings_job"
    )
    
    # Process transcription retries - run every 5 minutes
    scheduler.add_job(
        process_transcription_retries_job,
        'interval',
        minutes=5,
        id="process_transcription_retries_job"
    )
    
    # Start the scheduler
    scheduler.start()
    
    # Log the scheduled jobs
    jobs = [job.id for job in scheduler.get_jobs()]
    logger.info(f"Task scheduler started successfully with jobs: {', '.join(jobs)}")
    
    return scheduler