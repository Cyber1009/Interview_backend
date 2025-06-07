"""
Utility functions for slug generation and validation.
"""
import re
import uuid
from typing import Optional


def generate_slug_from_title(title: str, suffix: Optional[str] = None) -> str:
    """
    Generate a URL-friendly slug from an interview title.
    
    Args:
        title: The interview title to convert to a slug
        suffix: Optional unique suffix to append. If None, a random UUID suffix will be used.
    
    Returns:
        str: URL-friendly slug
    """
    # Convert to lowercase
    slug = title.lower()
    
    # Replace special chars with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Limit length to ensure db compatibility
    slug = slug[:40]
    
    # Add random suffix for uniqueness
    if suffix is None:
        # Use the first 8 chars of a UUID4
        suffix = str(uuid.uuid4())[:8]
    
    return f"{slug}-{suffix}"


def validate_slug(slug: str) -> bool:
    """
    Validate that a slug is in the proper format.
    
    Args:
        slug: The slug to validate
    
    Returns:
        bool: True if slug is valid, False otherwise
    """
    # Slugs should only contain lowercase letters, numbers, and hyphens
    # And should have at least one character before the final random suffix
    return bool(re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?-[a-z0-9]+$', slug))
