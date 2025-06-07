"""
Database migration module for schema updates and maintenance.
"""
import logging
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from app.core.database.db import get_db, engine
from app.core.database.models import Base
from app.core.config import settings
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of tables that are no longer needed after code edits
# Add your deprecated tables here
DEPRECATED_TABLES = [
    # Example: "old_interviews"
    "theme_schemas"  # This table is no longer needed since we merged into interview_schemas
]

def get_all_defined_tables():
    """Get all tables defined in SQLAlchemy models."""
    return [table.__tablename__ for table in Base.__subclasses__()]

def get_all_database_tables():
    """Get all tables currently in the database."""
    try:
        inspector = inspect(engine)
        return inspector.get_table_names()
    except Exception as e:
        logger.error(f"Error inspecting database: {e}")
        return []

def find_obsolete_tables():
    """
    Find tables in the database that are not defined in the models.
    These might be candidates for deprecation.
    
    Returns:
        list: List of potentially obsolete table names
    """
    defined_tables = get_all_defined_tables()
    db_tables = get_all_database_tables()
    
    # Tables to always ignore (migrations, SQLAlchemy internal tables, etc.)
    ignore_tables = ['alembic_version', 'spatial_ref_sys', 'pg_stat_statements']
    
    # Find tables in db that aren't in models
    obsolete_tables = [
        table for table in db_tables 
        if table not in defined_tables and table not in ignore_tables
        and not table.endswith('_deprecated')
        and not table.endswith('_backup')
    ]
    
    # Also add explicitly deprecated tables
    for table in DEPRECATED_TABLES:
        if table in db_tables and table not in obsolete_tables:
            obsolete_tables.append(table)
    
    return obsolete_tables

def generate_migration_commands():
    """
    Generate SQL commands to handle obsolete tables.
    
    Returns:
        dict: Dict with lists of SQL commands for different actions
    """
    obsolete_tables = find_obsolete_tables()
    timestamp = datetime.now().strftime("%Y%m%d")
    
    rename_commands = []
    backup_commands = []
    drop_commands = []
    
    for table in obsolete_tables:
        new_name = f"{table}_deprecated_{timestamp}"
        backup_name = f"{table}_backup_{timestamp}"
        
        rename_commands.append(f"ALTER TABLE {table} RENAME TO {new_name};")
        backup_commands.append(f"CREATE TABLE {backup_name} AS TABLE {table};")
        drop_commands.append(f"DROP TABLE {table};")
    
    return {
        'obsolete_tables': obsolete_tables,
        'rename_commands': rename_commands,
        'backup_commands': backup_commands, 
        'drop_commands': drop_commands
    }

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
    
    # Find obsolete tables automatically
    obsolete_tables = find_obsolete_tables()
    
    for table in obsolete_tables:
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
    logger.info("Starting database migration...")
    
    try:
        # Create connection
        with engine.connect() as connection:
            # Execute migrations in a transaction
            with connection.begin():
                # Check if company_name column exists in users table and rename it if needed
                connection.execute(text("""
                    DO $$
                    BEGIN
                        -- Check if company_name column exists but company doesn't
                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'users' AND column_name = 'company_name'
                        ) AND NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'users' AND column_name = 'company'
                        ) THEN
                            -- Rename company_name to company
                            ALTER TABLE users RENAME COLUMN company_name TO company;
                            RAISE NOTICE 'Renamed column company_name to company in users table';
                        END IF;

                        -- Check if company_name column exists but company doesn't in pending_accounts
                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'pending_accounts' AND column_name = 'company_name'
                        ) AND NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'pending_accounts' AND column_name = 'company'
                        ) THEN
                            -- Rename company_name to company
                            ALTER TABLE pending_accounts RENAME COLUMN company_name TO company;
                            RAISE NOTICE 'Renamed column company_name to company in pending_accounts table';
                        END IF;

                        -- Add company column if neither company nor company_name exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'users' AND (column_name = 'company' OR column_name = 'company_name')
                        ) THEN
                            -- Add the company column
                            ALTER TABLE users ADD COLUMN company VARCHAR;
                            RAISE NOTICE 'Added column company to users table';
                        END IF;

                        -- Add company column if neither company nor company_name exist in pending_accounts
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'pending_accounts' AND (column_name = 'company' OR column_name = 'company_name')
                        ) THEN
                            -- Add the company column
                            ALTER TABLE pending_accounts ADD COLUMN company VARCHAR;
                            RAISE NOTICE 'Added column company to pending_accounts table';
                        END IF;
                        
                        -- Add text_color column to user_themes if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'user_themes' AND column_name = 'text_color'                        ) THEN
                            -- Add the text_color column with default value
                            ALTER TABLE user_themes ADD COLUMN text_color VARCHAR DEFAULT '#222222';
                            RAISE NOTICE 'Added column text_color to user_themes table';
                        END IF;
                        
                        -- Remove secondary_color column if it exists
                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'user_themes' AND column_name = 'secondary_color'
                        ) THEN
                            -- Drop the secondary_color column
                            ALTER TABLE user_themes DROP COLUMN secondary_color;
                            RAISE NOTICE 'Removed column secondary_color from user_themes table';
                        END IF;
                        
                        -- Add analysis column to recordings table if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'recordings' AND column_name = 'analysis'
                        ) THEN
                            -- Add the analysis column
                            ALTER TABLE recordings ADD COLUMN analysis TEXT;
                            RAISE NOTICE 'Added column analysis to recordings table';
                        END IF;
                        
                        -- Add analysis_status column to recordings table if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'recordings' AND column_name = 'analysis_status'
                        ) THEN
                            -- Add the analysis_status column
                            ALTER TABLE recordings ADD COLUMN analysis_status VARCHAR DEFAULT 'pending';
                            RAISE NOTICE 'Added column analysis_status to recordings table';
                        END IF;
                        
                        -- Add analysis_error column to recordings table if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'recordings' AND column_name = 'analysis_error'
                        ) THEN
                            -- Add the analysis_error column
                            ALTER TABLE recordings ADD COLUMN analysis_error VARCHAR;
                            RAISE NOTICE 'Added column analysis_error to recordings table';
                        END IF;
                        
                        -- Add transcription_retry_count column to recordings table if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'recordings' AND column_name = 'transcription_retry_count'
                        ) THEN
                            -- Add the transcription_retry_count column with default value
                            ALTER TABLE recordings ADD COLUMN transcription_retry_count INTEGER DEFAULT 0;
                            RAISE NOTICE 'Added column transcription_retry_count to recordings table';
                        END IF;                        -- Add next_retry_at column to recordings table if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'recordings' AND column_name = 'next_retry_at'
                        ) THEN
                            -- Add the next_retry_at column
                            ALTER TABLE recordings ADD COLUMN next_retry_at TIMESTAMP WITH TIME ZONE;
                            RAISE NOTICE 'Added column next_retry_at to recordings table';
                        END IF;
                        
                        -- Rename owner_id to interviewer_id in interviews table if needed
                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'interviews' AND column_name = 'owner_id'
                        ) AND NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'interviews' AND column_name = 'interviewer_id'
                        ) THEN
                            -- Rename owner_id to interviewer_id
                            ALTER TABLE interviews RENAME COLUMN owner_id TO interviewer_id;
                            RAISE NOTICE 'Renamed column owner_id to interviewer_id in interviews table';
                        END IF;
                        
                        -- Add storage_type column to recordings table for S3 support if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'recordings' AND column_name = 'storage_type'
                        ) THEN
                            -- Add the storage_type column with default value of 'local'
                            ALTER TABLE recordings ADD COLUMN storage_type VARCHAR DEFAULT 'local';
                            RAISE NOTICE 'Added column storage_type to recordings table';
                        END IF;
                        
                        -- Add file_url column to recordings table for S3 presigned URLs if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'recordings' AND column_name = 'file_url'
                        ) THEN
                            -- Add the file_url column
                            ALTER TABLE recordings ADD COLUMN file_url VARCHAR;
                            RAISE NOTICE 'Added column file_url to recordings table';
                        END IF;
                          -- Add slug column to interviews table if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'interviews' AND column_name = 'slug'
                        ) THEN
                            -- Add the slug column
                            ALTER TABLE interviews ADD COLUMN slug VARCHAR UNIQUE;
                            
                            -- Generate slugs for existing interviews
                            -- Generate a base slug from title and add a random suffix for uniqueness
                            UPDATE interviews 
                            SET slug = LOWER(REGEXP_REPLACE(title, '[^a-zA-Z0-9]', '-', 'g')) || '-' || 
                                   SUBSTRING(MD5(RANDOM()::text), 1, 8)
                            WHERE slug IS NULL;
                            
                            RAISE NOTICE 'Added column slug to interviews table and generated slugs for existing interviews';
                        END IF;
                          -- Remove theme column from interviews table if it exists
                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'interviews' AND column_name = 'theme'
                        ) THEN
                            -- Drop the theme column
                            ALTER TABLE interviews DROP COLUMN theme;
                            RAISE NOTICE 'Removed column theme from interviews table';
                        END IF;
                        
                        -- Add company_logo_url column to user_themes table if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'user_themes' AND column_name = 'company_logo_url'
                        ) THEN
                            -- Add the company_logo_url column
                            ALTER TABLE user_themes ADD COLUMN company_logo_url VARCHAR;
                            RAISE NOTICE 'Added column company_logo_url to user_themes table';
                        END IF;
                        
                        -- Add company_logo_s3_key column to user_themes table if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'user_themes' AND column_name = 'company_logo_s3_key'
                        ) THEN
                            -- Add the company_logo_s3_key column
                            ALTER TABLE user_themes ADD COLUMN company_logo_s3_key VARCHAR;
                            RAISE NOTICE 'Added column company_logo_s3_key to user_themes table';
                        END IF;
                        -- Add storage_type column to user_themes table if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'user_themes' AND column_name = 'storage_type'
                        ) THEN
                            -- Add the storage_type column with default value of 'local'
                            ALTER TABLE user_themes ADD COLUMN storage_type VARCHAR DEFAULT 'local';
                            RAISE NOTICE 'Added column storage_type to user_themes table';
                        END IF;

                        -- Add enhanced token system fields to tokens table
                        -- Add candidate_name column if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'tokens' AND column_name = 'candidate_name'
                        ) THEN
                            ALTER TABLE tokens ADD COLUMN candidate_name VARCHAR;
                            RAISE NOTICE 'Added column candidate_name to tokens table';
                        END IF;

                        -- Add expires_at column if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'tokens' AND column_name = 'expires_at'
                        ) THEN
                            ALTER TABLE tokens ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE;
                            RAISE NOTICE 'Added column expires_at to tokens table';
                        END IF;

                        -- Add max_attempts column if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'tokens' AND column_name = 'max_attempts'
                        ) THEN
                            ALTER TABLE tokens ADD COLUMN max_attempts INTEGER DEFAULT 1;
                            RAISE NOTICE 'Added column max_attempts to tokens table';
                        END IF;

                        -- Add current_attempts column if it doesn't exist
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'tokens' AND column_name = 'current_attempts'
                        ) THEN
                            ALTER TABLE tokens ADD COLUMN current_attempts INTEGER DEFAULT 0;
                            RAISE NOTICE 'Added column current_attempts to tokens table';
                        END IF;
                    END $$;
                """))
            
            logger.info("Database migration completed successfully")
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        raise
        
    return True

def print_migration_status():
    """
    Print information about obsolete tables and suggested migration commands.
    Useful for diagnosing database schema issues.
    """
    obsolete = find_obsolete_tables()
    
    if obsolete:
        print("The following tables may be obsolete and candidates for deprecation:")
        for table in obsolete:
            print(f" - {table}")
        
        commands = generate_migration_commands()
        
        print("\nTo safely rename these tables in production (keeping the data):")
        for cmd in commands['rename_commands']:
            print(f"  {cmd}")
            
        print("\nTo back up and then drop these tables in development:")
        for i, table in enumerate(commands['obsolete_tables']):
            print(f"  -- For {table}:")
            print(f"  {commands['backup_commands'][i]}")
            print(f"  {commands['drop_commands'][i]}")
    else:
        print("No obsolete tables found in the database.")

if __name__ == "__main__":
    # This allows running the migration directly with: python -m app.core.database.migrations
    migrate_database()
    # You can also uncomment the line below to see migration status information
    # print_migration_status()