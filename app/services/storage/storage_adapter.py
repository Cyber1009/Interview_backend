"""
Storage adapter interface for abstracting storage operations.
This allows changing the storage backend without modifying the application code.
"""
from abc import ABC, abstractmethod
from typing import BinaryIO, List, Optional, Tuple, Dict

class StorageAdapter(ABC):
    """
    Abstract base class for storage adapters.
    Implementations should provide methods for saving, retrieving, and deleting files.
    """
    
    @abstractmethod
    async def save(self, file_content: bytes, prefix: str, file_extension: str) -> str:
        """
        Save file content to storage.
        
        Args:
            file_content: Binary content of the file
            prefix: Prefix for the filename (e.g., session_123)
            file_extension: File extension including the dot (e.g., .mp3)
            
        Returns:
            File path or identifier where the file was saved
        """
        pass
    
    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: Path or identifier of the file to delete
            
        Returns:
            True if file was deleted, False otherwise
        """
        pass
    
    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            file_path: Path or identifier of the file to check
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Get a URL to access the file.
        
        Args:
            file_path: Path or identifier of the file
            expires_in: Expiration time in seconds for pre-signed URLs
            
        Returns:
            URL to access the file
        """
        pass
