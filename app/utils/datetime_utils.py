"""
Utility functions for consistent datetime handling.
"""
from datetime import datetime, timezone

def get_utc_now():
    """Get current time as timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

def make_aware(dt):
    """Convert naive datetime to timezone-aware UTC datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

def safe_compare_dates(date1, date2):
    """Safely compare two datetimes, ensuring both are timezone-aware."""
    if date1 is None or date2 is None:
        return False
    aware_date1 = make_aware(date1)
    aware_date2 = make_aware(date2)
    return aware_date1 < aware_date2
