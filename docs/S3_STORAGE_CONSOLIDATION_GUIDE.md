# S3 Storage Consolidation Guide

This guide explains how to test and use the new consolidated S3 storage implementation.

## Introduction

The S3 storage implementation has been consolidated to eliminate redundancy and improve maintainability. The new implementation combines the functionality of the previous `s3_storage.py` and `s3_storage_adapter.py` files into a single file `consolidated_s3_storage.py`.

## Testing the Consolidated Implementation

To run the tests for the consolidated S3 storage implementation:

```bash
# Run the consolidated S3 storage tests
python -m pytest tests/test_consolidated_s3_storage.py -v

# Run all S3-related tests to ensure compatibility
python -m pytest tests/test_s3*.py -v
```

## Using the Consolidated Implementation

### Via StorageFactory (Recommended)

The StorageFactory has been updated to use the new consolidated implementation:

```python
from app.services.storage.storage_factory import get_storage

# Get the default storage adapter (S3 or local based on configuration)
storage = get_storage()

# Use the storage adapter
file_path = await storage.save(file_content, "prefix", ".mp3")
url = storage.get_url(file_path)
```

### Direct Usage

You can also use the S3Storage class directly:

```python
from app.services.storage.consolidated_s3_storage import S3Storage

# Initialize S3 storage
s3_storage = S3Storage()

# Use S3 storage methods
file_path = await s3_storage.save(file_content, "prefix", ".mp3")
url = s3_storage.get_url(file_path)
downloaded_content = await s3_storage.download_bytes(file_path)
```

## Migration Steps

1. ✅ Replace imports from old files:
   - Replace `from app.services.storage.s3_storage import S3StorageService` with `from app.services.storage.consolidated_s3_storage import S3Storage`
   - Replace `from app.services.storage.s3_storage_adapter import S3StorageAdapter` with `from app.services.storage.consolidated_s3_storage import S3Storage`

2. ✅ Update method calls:
   - Replace `s3_service.upload_file()` with `s3_storage.save()`
   - Replace `s3_service.delete_file()` with `s3_storage.delete()`
   - Replace `s3_service.file_exists()` with `s3_storage.exists()`
   - Replace `s3_service.get_presigned_url()` with `s3_storage.get_url()`

3. ✅ Use the StorageFactory when possible instead of direct instantiation

## Benefits of the Consolidated Implementation

- Reduced code duplication
- Simplified maintenance
- More consistent API
- Better error handling
- Improved testability

## Rollback Plan

If issues arise with the consolidated implementation, you can temporarily revert to the previous implementation by updating `storage_factory.py` to use the old S3StorageAdapter class.
