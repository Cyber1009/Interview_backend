"""
Storage factory module for creating and managing storage adapters.
This allows the application to use different storage backends based on configuration.
"""
from typing import Dict, Type
import logging

from app.core.config import settings
from app.services.storage.storage_adapter import StorageAdapter

# Configure logging
logger = logging.getLogger(__name__)

class StorageFactory:
    """Factory for creating and managing storage adapters."""
    # Registry will be populated dynamically
    _adapters: Dict[str, Type[StorageAdapter]] = {}
    
    # Default adapter instance
    _default_adapter = None
    @classmethod
    def _ensure_adapters_loaded(cls):
        """Ensure adapters are loaded into the registry."""
        if not cls._adapters:
            # Import here to avoid circular imports
            from app.services.storage.local_storage import LocalStorage
            from app.services.storage.s3_storage import S3Storage
            
            cls._adapters = {
                "local": LocalStorage,
                "s3": S3Storage,
            }
    
    @classmethod
    def get_adapter(cls, adapter_type: str = None) -> StorageAdapter:
        """
        Get a storage adapter instance.
        
        Args:
            adapter_type: Type of storage adapter to use. If None, uses the configured default.
            
        Returns:
            Instance of a StorageAdapter
        """
        # Ensure adapters are loaded
        cls._ensure_adapters_loaded()
        
        # If default adapter already exists, return it
        if adapter_type is None and cls._default_adapter is not None:
            return cls._default_adapter
        
        # Determine which adapter to use
        if adapter_type is None:
            # Automatically choose S3 if configured for video storage, otherwise local
            if settings.should_use_s3:
                adapter_type = "s3"
                logger.info("Using S3 storage adapter (based on USE_S3_FOR_VIDEO=true)")
            else:
                adapter_type = "local"

        else:
            # Use explicitly specified adapter type
            adapter_type = adapter_type or getattr(settings, "STORAGE_ADAPTER", "local")
        
        if adapter_type not in cls._adapters:
            logger.warning(f"Storage adapter '{adapter_type}' not found. Using 'local' instead.")
            adapter_type = "local"
        
        # Create the adapter
        adapter_class = cls._adapters[adapter_type]
        try:
            adapter = adapter_class()
            
            # Store as default if not specified otherwise
            if cls._default_adapter is None:
                cls._default_adapter = adapter
            
            return adapter
        except Exception as e:
            logger.error(f"Failed to initialize storage adapter '{adapter_type}': {e}")
            # Fall back to local storage if S3 initialization fails
            if adapter_type == "s3":
                logger.info("Falling back to local storage")
                return cls.get_adapter("local")
            raise
    
    @classmethod
    def register_adapter(cls, name: str, adapter_class: Type[StorageAdapter]):
        """
        Register a new storage adapter.
        
        Args:
            name: Name of the adapter
            adapter_class: Class of the adapter (must extend StorageAdapter)
        """
        if not issubclass(adapter_class, StorageAdapter):
            raise ValueError(f"Adapter class must inherit from StorageAdapter")
        
        cls._adapters[name] = adapter_class
        logger.info(f"Registered storage adapter: {name}")

# Create a convenience function for getting the default storage adapter
def get_storage() -> StorageAdapter:
    """Get the default storage adapter."""
    return StorageFactory.get_adapter()