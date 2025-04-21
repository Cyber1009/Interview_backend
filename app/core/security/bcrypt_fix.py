"""
Patch for bcrypt compatibility with passlib.
This file monkey patches the bcrypt module to make it compatible with passlib.
"""
import logging
import bcrypt
import sys

# Configure logging
logger = logging.getLogger(__name__)

def apply_bcrypt_patch():
    """
    Apply a compatibility patch to bcrypt to work with passlib.
    
    This function creates a fake __about__ module with __version__ attribute
    to satisfy passlib's expectations. It should be called as early as possible
    in the application startup process.
    """
    # Check if bcrypt needs to be patched
    if not hasattr(bcrypt, '__about__'):
        logger.info("Applying bcrypt patch for passlib compatibility")
        
        # Get the actual bcrypt version or fall back to a safe default
        bcrypt_version = getattr(bcrypt, '__version__', '4.0.0')
        
        # Create a fake __about__ module with a __version__ attribute
        class FakeAbout:
            __version__ = bcrypt_version
        
        # Add it to bcrypt
        bcrypt.__about__ = FakeAbout()
        
        # Add the fake version attribute to the module's dict directly
        # This ensures proper attribute access in all contexts
        if not hasattr(bcrypt.__about__, '__version__'):
            setattr(bcrypt.__about__, '__version__', bcrypt_version)
        
        logger.info(f"Patched bcrypt with version: {bcrypt.__about__.__version__}")
        return True
    return False

# Apply the patch immediately when this module is imported
patched = apply_bcrypt_patch()