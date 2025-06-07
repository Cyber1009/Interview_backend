"""
AWS S3 storage service implementing the StorageAdapter interface.
This module provides a complete S3 storage solution for the interview app.
"""
from datetime import datetime
from typing import BinaryIO, List, Optional, Tuple, Dict, Any
import logging
import uuid
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from io import BytesIO

from app.services.storage.storage_adapter import StorageAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)

class S3Storage(StorageAdapter):
    """
    AWS S3 implementation of the StorageAdapter interface.
    This class combines functionality previously split between S3StorageService
    and S3StorageAdapter into a single, cohesive implementation.
    """
    
    def __init__(self):
        """
        Initialize S3 storage adapter with AWS credentials and settings.
        Raises:
            ValueError: If S3 is not configured or disabled
            NoCredentialsError: If AWS credentials are missing
            ClientError: If connection to S3 fails
        """
        if not settings.should_use_s3:
            raise ValueError("S3 is not configured or disabled. Check AWS credentials and USE_S3_FOR_VIDEO setting.")
        
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self.region = settings.AWS_REGION
        
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.region
            )            # Test connection
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 client initialized successfully for bucket: {self.bucket_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except ClientError as e:
            logger.error(f"Error connecting to S3: {e}")
            raise
    
    async def save(self, file_content: bytes, prefix: str, file_extension: str) -> str:
        """
        Save file content to S3.
        
        Args:
            file_content: Binary content of the file
            prefix: Prefix for the filename (e.g., session_123)
            file_extension: File extension including the dot (e.g., .mp3)
            
        Returns:
            S3 key where the file was saved
        """
        # Generate S3 key with timestamp and UUID for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        s3_key = f"recordings/{prefix}_{timestamp}_{unique_id}{file_extension}"
        
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=self._get_content_type(file_extension),
                Metadata={
                    'uploaded_at': datetime.utcnow().isoformat(),
                    'prefix': prefix,
                    'original_extension': file_extension
                }
            )
            logger.info(f"File uploaded successfully to S3: {s3_key}")
            return s3_key
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise
    
    def delete(self, file_path: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            file_path: S3 key of the file to delete
            
        Returns:
            True if file was deleted, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            logger.info(f"File deleted from S3: {file_path}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            return False
    
    def exists(self, file_path: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            file_path: S3 key of the file to check
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            return True
        except ClientError:
            return False
    
    def get_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Get a presigned URL to access the file in S3.
        
        Args:
            file_path: S3 key of the file
            expires_in: Expiration time in seconds for pre-signed URLs
            
        Returns:
            Presigned URL to access the file
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_path
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise
    
    async def download_bytes(self, key: str) -> bytes:
        """
        Download a file from S3.
        
        Args:
            key: The S3 key (path) of the file
            
        Returns:
            The file content as bytes
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            raise
    
    def get_file_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata from S3.
        
        Args:
            key: The S3 key (path) of the file
            
        Returns:
            Dictionary with file metadata or None if file doesn't exist
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            # Convert to a more friendly format
            return {
                'size': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified'),
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError:
            return None
    
    def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """
        List files in S3 with the given prefix.
        
        Args:
            prefix: S3 key prefix to filter files
            
        Returns:
            List of file information dictionaries
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            for item in response.get('Contents', []):
                files.append({
                    'key': item.get('Key'),
                    'size': item.get('Size', 0),
                    'last_modified': item.get('LastModified')
                })
            
            return files
        except ClientError as e:
            logger.error(f"Failed to list files in S3: {e}")
            return []
    
    def _get_content_type(self, file_extension: str) -> str:
        """
        Get the appropriate Content-Type for a file extension.
        
        Args:
            file_extension: File extension including the dot (e.g., .mp3)
            
        Returns:
            MIME type string
        """
        content_type_map = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.webm': 'audio/webm',
            '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mov': 'video/quicktime'
        }
        return content_type_map.get(file_extension.lower(), 'application/octet-stream')