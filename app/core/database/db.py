"""
Database connection module for the Interview Backend application.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to connect to PostgreSQL, fall back to SQLite if it fails
try:
    # Create PostgreSQL engine
    engine = create_engine(settings.DATABASE_URL)
    # Test the connection
    with engine.connect() as conn:
        logger.info("Successfully connected to PostgreSQL database")
except Exception as e:
    if settings.DEV_MODE:
        logger.warning(f"PostgreSQL connection failed: {e}. Using SQLite as fallback.")
        # Create SQLite engine as fallback
        engine = create_engine(
            settings.SQLITE_URL, 
            connect_args={"check_same_thread": False}
        )
    else:
        # In production, we want to fail if the database connection fails
        logger.error(f"Database connection failed: {e}")
        raise e

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()