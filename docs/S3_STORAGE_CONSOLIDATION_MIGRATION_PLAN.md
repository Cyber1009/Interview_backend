# S3 Storage Consolidation Migration Guide

This document outlines the process of migrating from the separate S3 storage service and adapter to the new consolidated S3 storage implementation.

## Overview

We've consolidated the following files:
- `s3_storage.py` (S3StorageService)
- `s3_storage_adapter.py` (S3StorageAdapter)

Into a single implementation:
- `consolidated_s3_storage.py` (S3Storage)

This consolidation simplifies the codebase, reduces duplication, and makes the storage layer more maintainable.

## Steps to Migrate

### 1. Update Imports

Replace any imports of the old classes with the new consolidated class:

```python
# Old imports
from app.services.storage.s3_storage import S3StorageService
from app.services.storage.s3_storage_adapter import S3StorageAdapter

# New import
from app.services.storage.consolidated_s3_storage import S3Storage
```

### 2. Replace Service and Adapter Usage

Replace any instantiation of the old classes:

```python
# Old code
s3_service = S3StorageService()
s3_adapter = S3StorageAdapter()

# New code
s3_storage = S3Storage()
```

### 3. Method Mapping

The following table shows how methods from the old classes map to the new consolidated class:

| Old Method (S3StorageService) | New Method (S3Storage) |
|-------------------------------|------------------------|
| `upload_bytes(file_content, key, content_type)` | `save(file_content, prefix, file_extension)` |
| `download_bytes(key)` | `download_bytes(key)` |
| `delete_file(key)` | `delete(file_path)` |
| `get_presigned_url(key, expires_in)` | `get_url(file_path, expires_in)` |
| `file_exists(key)` | `exists(file_path)` |
| `get_file_info(key)` | `get_file_info(key)` |

| Old Method (S3StorageAdapter) | New Method (S3Storage) |
|-------------------------------|------------------------|
| `save(file_content, prefix, file_extension)` | `save(file_content, prefix, file_extension)` |
| `delete(file_path)` | `delete(file_path)` |
| `exists(file_path)` | `exists(file_path)` |
| `get_url(file_path, expires_in)` | `get_url(file_path, expires_in)` |

### 4. Update Factory References

The `StorageFactory` class has been updated to use the new consolidated implementation. No changes are required if you're using the factory to get storage adapters.

### 5. Testing

Make sure to test your application thoroughly after migrating to ensure everything works as expected.

## Deprecation Timeline

The old S3 storage files will be deprecated and removed in a future version. Please migrate to the new consolidated implementation as soon as possible.