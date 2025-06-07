"""
Local file storage implementation of the StorageAdapter interface.
Handles file operations on the local filesystem.
"""
import os
import logging
import uuid
import shutil
from typing import BinaryIO, List, Optional, Tuple
from urllib.parse import urljoin

from app.services.storage.storage_adapter import StorageAdapter
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class LocalStorage(StorageAdapter):
    """
    Implementation of StorageAdapter for local file storage.
    Stores files on the local filesystem.
    """
    def __init__(self, base_dir: str = "uploads"):
        """
        Initialize the file storage service.
        
        Args:
            base_dir: Base directory for file storage
        """
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
    
    async def save(self, file_content: bytes, prefix: str, file_extension: str) -> str:
        """
        Save file content to disk.
        
        Args:
            file_content: Binary content of the file
            prefix: Prefix for the filename (e.g., session_123)
            file_extension: File extension including the dot (e.g., .mp3)
            
        Returns:
            File path where the file was saved
        """
        # Create directory if it doesn't exist
        directory = os.path.join(self.base_dir, "recordings")
        os.makedirs(directory, exist_ok=True)
        
        # Generate unique filename
        filename = f"{prefix}_{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(directory, filename)
        
        try:
            # Write file to disk
            with open(file_path, 'wb') as out_file:
                out_file.write(file_content)
            logger.info(f"File saved successfully: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise
    
    def delete(self, file_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if file was deleted, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File deleted successfully: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {str(e)}")
            return False
    
    def exists(self, file_path: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file exists, False otherwise
        """
        return os.path.exists(file_path)
    
    def get_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Get a URL to access the file.
        For local storage, this returns a relative URL.
        
        Args:
            file_path: Path of the file
            expires_in: Not used for local storage
            
        Returns:
            URL to access the file
        """
        # Take just the relative path from the uploads directory
        if self.base_dir in file_path:
            relative_path = file_path.split(self.base_dir)[1]
            if relative_path.startswith('/') or relative_path.startswith('\\'):
                relative_path = relative_path[1:]
            
            # Create a URL that the web application can use
            base_url = settings.BASE_URL if hasattr(settings, 'BASE_URL') else "/"
            return urljoin(base_url, f"uploads/{relative_path}")
        
        return file_path  # Return as-is if not in the expected format
    
    def cleanup_old_files(self, directory: str, days_old: int = 30) -> Tuple[int, List[str]]:
        """
        Clean up files older than a certain number of days.
        
        Args:
            directory: Directory to clean up
            days_old: Delete files older than this many days
            
        Returns:
            Tuple of (number of files deleted, list of deleted files)
        """
        import time
        from datetime import datetime, timedelta
        
        cutoff_time = time.time() - (days_old * 86400)
        deleted_count = 0
        deleted_files = []
        
        try:
            target_dir = os.path.join(self.base_dir, directory)
            if not os.path.exists(target_dir):
                logger.warning(f"Directory does not exist for cleanup: {target_dir}")
                return 0, []
                
            for filename in os.listdir(target_dir):
                file_path = os.path.join(target_dir, filename)
                if os.path.isfile(file_path):
                    file_stat = os.stat(file_path)
                    if file_stat.st_mtime < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                        deleted_files.append(file_path)
                        logger.info(f"Deleted old file: {file_path}")
            
            return deleted_count, deleted_files
        except Exception as e:
            logger.error(f"Error cleaning up old files: {str(e)}")
            return 0, []
