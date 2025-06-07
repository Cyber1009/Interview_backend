"""
Database connection management.
"""
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import logging
import time
import os
from typing import Dict, Any

from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Database connection URL
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Create database engine with production configuration
# SQLite code is commented out since it's not needed for deployment
"""
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # SQLite configuration - primarily for development
    logger.info("Using SQLite database configuration")
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        # Set reasonable pool size for development
        pool_size=5,
        max_overflow=10
    )
else:
"""
# PostgreSQL configuration
logger.info("Using PostgreSQL/production database configuration")
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # Configure connection pooling for production workloads
    pool_size=20,  # Reasonable default for moderate traffic
    max_overflow=40,  # Allow up to additional 40 connections under high load
    pool_timeout=30,  # 30 seconds timeout for getting a connection
    pool_recycle=1800  # Recycle connections every 30 minutes
)

# Create session factory - use scoped_session for thread safety
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

# Create base class for models
Base = declarative_base()

# Database dependency
def get_db():
    """
    Get a database session.
    
    Creates a new database session for a request and ensures it is closed when the request is complete.
    This function is used as a FastAPI dependency.
    
    Yields:
        SQLAlchemy Session: A database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_status(db=None) -> Dict[str, Any]:
    """
    Get database connection status and information.
    
    Args:
        db (Session, optional): An existing database session. If not provided, a new one will be created.
        
    Returns:
        Dict containing database status information
    """
    if db is None:
        db = next(get_db())
        
    try:
        # Check connection by running a simple query
        start_time = time.time()
        db.execute("SELECT 1")
        query_time = time.time() - start_time
        
        # Get database information using inspector
        inspector = inspect(engine)
        
        # Count tables
        table_count = len(inspector.get_table_names())
        
        return {
            "status": "connected",
            "response_time_ms": round(query_time * 1000, 2),
            "table_count": table_count,
            "engine": str(engine.url.drivername),
            "pooling": {
                "pool_size": engine.pool.size(),
                "checkedin": engine.pool.checkedin(),
                "overflow": engine.pool.overflow(),
                "checkedout": engine.pool.checkedout()
            }
        }
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
        }