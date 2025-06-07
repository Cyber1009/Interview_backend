"""
File utility functions for handling file operations.
"""
import os
import uuid
import hashlib
from datetime import datetime
from typing import Optional


def generate_unique_filename(
    prefix: str = "", 
    extension: str = "", 
    timestamp: bool = True, 
    uuid_suffix: bool = True
) -> str:
    """
    Generate a unique filename with optional prefix, timestamp, and UUID.
    
    Args:
        prefix: Optional prefix for the filename
        extension: File extension (with or without leading dot)
        timestamp: Whether to include timestamp in filename
        uuid_suffix: Whether to include UUID suffix for uniqueness
        
    Returns:
        Unique filename string
        
    Example:
        generate_unique_filename("session_1_question_2", ".mp3")
        # Returns: "session_1_question_2_20240606_143022_a1b2c3d4.mp3"
    """
    parts = []
    
    # Add prefix if provided
    if prefix:
        parts.append(prefix)
    
    # Add timestamp if requested
    if timestamp:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        parts.append(timestamp_str)
    
    # Add UUID suffix if requested
    if uuid_suffix:
        uuid_str = str(uuid.uuid4()).replace('-', '')[:8]
        parts.append(uuid_str)
    
    # Join parts with underscores
    filename = "_".join(parts)
    
    # Ensure extension starts with dot
    if extension and not extension.startswith('.'):
        extension = f".{extension}"
    
    return f"{filename}{extension}"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing or replacing invalid characters.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    # Replace invalid characters with underscores
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Limit length to 255 characters (most filesystems)
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        max_name_length = 255 - len(ext)
        filename = name[:max_name_length] + ext
    
    return filename


def get_file_extension(filename: str) -> str:
    """
    Get the file extension from a filename.
    
    Args:
        filename: The filename
        
    Returns:
        File extension including the dot (e.g., '.mp3')
    """
    return os.path.splitext(filename)[1].lower()


def get_file_hash(file_content: bytes, algorithm: str = 'sha256') -> str:
    """
    Generate a hash of file content.
    
    Args:
        file_content: The file content as bytes
        algorithm: Hash algorithm to use ('sha256', 'md5', etc.)
        
    Returns:
        Hexadecimal hash string
    """
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(file_content)
    return hash_obj.hexdigest()


def validate_file_size(file_content: bytes, max_size_mb: int = 100) -> bool:
    """
    Validate that file size is within limits.
    
    Args:
        file_content: The file content as bytes
        max_size_mb: Maximum allowed size in MB
        
    Returns:
        True if file size is valid, False otherwise
    """
    file_size_mb = len(file_content) / (1024 * 1024)
    return file_size_mb <= max_size_mb


def get_content_type(file_extension: str) -> str:
    """
    Get the MIME content type for a file extension.
    
    Args:
        file_extension: File extension (with or without leading dot)
        
    Returns:
        MIME content type string
    """
    # Ensure extension starts with dot
    if not file_extension.startswith('.'):
        file_extension = f".{file_extension}"
    
    content_types = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.ogg': 'audio/ogg',
        '.webm': 'audio/webm',
        '.mp4': 'video/mp4',
        '.avi': 'video/avi',
        '.mov': 'video/quicktime',
        '.mkv': 'video/x-matroska',
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif'
    }
    
    return content_types.get(file_extension.lower(), 'application/octet-stream')
