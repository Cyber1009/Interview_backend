"""
Utility functions for database management.
"""
import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings
from app.core.database.models import Base
from datetime import datetime

logger = logging.getLogger(__name__)

def get_all_defined_tables():
    """Get all tables defined in SQLAlchemy models."""
    return [table.__tablename__ for table in Base.__subclasses__()]

def get_all_database_tables():
    """Get all tables currently in the database."""
    try:
        engine = create_engine(settings.DATABASE_URL)
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

if __name__ == "__main__":
    # This allows running the utility directly to identify obsolete tables
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