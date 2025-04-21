"""
Database migration module for schema updates and maintenance.
"""
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database.db import get_db, engine
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of tables that are no longer needed after code edits
# Add your deprecated tables here
DEPRECATED_TABLES = [
    # Example: "old_interviews"
]

def handle_deprecated_tables(db: Session):
    """
    Handle tables that are no longer needed after code edits.
    Options:
    1. Rename them with a '_deprecated' suffix
    2. Create a backup
    3. Drop them if in development mode
    
    Uses SQLAlchemy session management for consistency with the rest of the application.
    """
    # Get environment (development or production)
    env = os.getenv("APP_ENV", "development")
    
    for table in DEPRECATED_TABLES:
        # Check if table exists
        result = db.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = '{table}'
            )
        """))
        table_exists = result.scalar()
        
        if not table_exists:
            logger.info(f"Table {table} does not exist, skipping")
            continue
            
        # Handle based on environment
        timestamp = datetime.now().strftime("%Y%m%d")
        
        if env == "production":
            # In production: rename tables with deprecated suffix and timestamp
            new_name = f"{table}_deprecated_{timestamp}"
            logger.info(f"Renaming deprecated table {table} to {new_name}")
            db.execute(text(f"ALTER TABLE {table} RENAME TO {new_name}"))
            db.commit()
            logger.info(f"Table {table} renamed to {new_name}")
        else:
            # In development: create a backup and then drop
            backup_name = f"{table}_backup_{timestamp}"
            logger.info(f"Creating backup of table {table} as {backup_name}")
            
            # Create backup
            db.execute(text(f"CREATE TABLE {backup_name} AS TABLE {table}"))
            db.commit()
            
            # Drop original table
            logger.info(f"Dropping deprecated table {table}")
            db.execute(text(f"DROP TABLE {table}"))
            db.commit()
            
        logger.info(f"Successfully handled deprecated table {table}")

def migrate_database():
    """
    Run database migrations to update schema when needed.
    Using SQLAlchemy session management for consistency with the rest of the application.
    """
    try:
        # Get a database session
        for db in get_db():
            # Handle deprecated tables first
            handle_deprecated_tables(db)
            
            # Check if subscription_plan column exists
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'subscription_plan'
            """))
            has_subscription_plan = result.fetchone() is not None
            
            # Add subscription_plan column if it doesn't exist
            if not has_subscription_plan:
                logger.info("Adding subscription_plan column to users table")
                db.execute(text("ALTER TABLE users ADD COLUMN subscription_plan VARCHAR"))
                db.commit()
            
            # Check if subscription_status column exists
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'subscription_status'
            """))
            has_subscription_status = result.fetchone() is not None
            
            # Add subscription_status column if it doesn't exist
            if not has_subscription_status:
                logger.info("Adding subscription_status column to users table")
                db.execute(text("ALTER TABLE users ADD COLUMN subscription_status VARCHAR DEFAULT 'inactive'"))
                db.commit()
            
            # Check if payment_method_id column exists
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'payment_method_id'
            """))
            has_payment_method_id = result.fetchone() is not None
            
            # Add payment_method_id column if it doesn't exist
            if not has_payment_method_id:
                logger.info("Adding payment_method_id column to users table")
                db.execute(text("ALTER TABLE users ADD COLUMN payment_method_id VARCHAR"))
                db.commit()
            
            # Check if user_themes table exists
            result = db.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_themes'
                )
            """))
            user_themes_exists = result.scalar()
            
            if not user_themes_exists:
                logger.info("Creating user_themes table")
                db.execute(text("""
                    CREATE TABLE user_themes (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER UNIQUE REFERENCES users(id),
                        company_logo VARCHAR,
                        primary_color VARCHAR DEFAULT '#3498db',
                        secondary_color VARCHAR DEFAULT '#2ecc71',
                        accent_color VARCHAR DEFAULT '#e74c3c',
                        background_color VARCHAR DEFAULT '#f5f5f5',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE
                    )
                """))
                db.commit()
            
            # Check if preparation_time column exists in questions table
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'questions' AND column_name = 'preparation_time'
            """))
            has_preparation_time = result.fetchone() is not None
            
            if not has_preparation_time:
                logger.info("Adding preparation_time column to questions table")
                db.execute(text("ALTER TABLE questions ADD COLUMN preparation_time FLOAT DEFAULT 30.0"))
                db.commit()
            
            # Check if responding_time column exists in questions table
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'questions' AND column_name = 'responding_time'
            """))
            has_responding_time = result.fetchone() is not None
            
            if not has_responding_time:
                logger.info("Adding responding_time column to questions table")
                db.execute(text("ALTER TABLE questions ADD COLUMN responding_time FLOAT DEFAULT 60.0"))
                db.commit()
            
            # Check if transcription_status column exists in recordings table
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'recordings' AND column_name = 'transcription_status'
            """))
            has_transcription_status = result.fetchone() is not None
            
            if not has_transcription_status:
                logger.info("Adding transcription_status column to recordings table")
                db.execute(text("ALTER TABLE recordings ADD COLUMN transcription_status VARCHAR DEFAULT 'pending'"))
                db.execute(text("ALTER TABLE recordings ADD COLUMN transcription_error VARCHAR"))
                db.commit()
            
            # Exit after completed
            break
        
        logger.info("Database migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        return False

if __name__ == "__main__":
    # This allows running the migration directly with: python -m app.core.database.migrations
    migrate_database()