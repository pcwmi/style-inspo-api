"""
Storage Manager - Abstract layer for local and cloud storage

Supports both local filesystem (dev) and AWS S3 (production).
"""

import os
import json
import logging
from typing import Dict, Optional, Union
from io import BytesIO
from PIL import Image

try:
    from botocore.exceptions import ClientError
except ImportError:
    ClientError = None  # Will be caught if boto3 not available

logger = logging.getLogger(__name__)


class StorageManager:
    """Unified interface for local and cloud storage"""
    
    def __init__(self, storage_type: str = "local", user_id: str = "default"):
        self.user_id = user_id
        
        # Normalize storage_type: handle empty strings, None, or invalid values
        if not storage_type or storage_type.strip() == "":
            storage_type = "local"
        else:
            storage_type = storage_type.strip().lower()
        
        # Try to initialize S3, fallback to local if it fails
        if storage_type == "s3":
            try:
                self._init_s3_client()
                self.storage_type = "s3"
                print(f"✅ Using S3 storage for user: {user_id}")
            except Exception as e:
                print(f"⚠️ WARNING: Failed to initialize S3: {e}")
                print("⚠️ WARNING: Falling back to local storage - data will NOT persist across app restarts")
                print("⚠️ WARNING: Please check AWS credentials in environment variables")
                # Log warning (no UI dependencies)
                logger.warning("Storage Mode: Using local storage (ephemeral). S3 credentials may be missing. Data will not persist.")
                self._init_local_storage()
                self.storage_type = "local"
        elif storage_type == "local":
            self._init_local_storage()
            self.storage_type = "local"
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")
    
    def _init_local_storage(self):
        """Initialize local filesystem storage"""
        self.base_path = os.path.join("wardrobe_photos", self.user_id)
        self.items_path = os.path.join(self.base_path, "items")
        
        # Ensure directories exist
        os.makedirs(self.items_path, exist_ok=True)
    
    def _init_s3_client(self):
        """Initialize AWS S3 client"""
        try:
            import boto3
            from core.config import settings

            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            # Support both variable names for backward compatibility
            self.bucket_name = os.getenv('S3_BUCKET_NAME') or settings.AWS_S3_BUCKET
            self.s3_region = os.getenv('S3_REGION', 'us-east-1')
            
            if not self.bucket_name:
                raise ValueError("S3_BUCKET_NAME or AWS_S3_BUCKET environment variable must be set")
                
        except ImportError:
            raise ImportError("boto3 not installed. Run: pip install boto3")
    
    def get_base_url(self) -> str:
        """Return base URL for the storage"""
        if self.storage_type == "s3":
            return f"https://{self.bucket_name}.s3.{self.s3_region}.amazonaws.com"
        return self.base_path
    
    def save_image(self, image: Image.Image, filename: str) -> str:
        """
        Save image and return URL or path
        
        Args:
            image: PIL Image object
            filename: Target filename
            
        Returns:
            URL (S3) or path (local)
        """
        if self.storage_type == "s3":
            return self._save_to_s3(image, filename)
        else:
            return self._save_to_local(image, filename)
    
    def _save_to_local(self, image: Image.Image, filename: str) -> str:
        """Save image to local filesystem"""
        file_path = os.path.join(self.items_path, filename)
        
        # Resize if too large
        image.thumbnail((800, 800), Image.Resampling.LANCZOS)
        image.save(file_path, quality=85, optimize=True)
        
        return file_path
    
    def _save_to_s3(self, image: Image.Image, filename: str) -> str:
        """Upload image to S3"""
        s3_key = f"{self.user_id}/items/{filename}"
        
        # Resize if too large
        image.thumbnail((800, 800), Image.Resampling.LANCZOS)
        
        # Convert to bytes
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=85, optimize=True)
        buffer.seek(0)
        
        # Upload to S3 (no ACL needed - bucket policy handles public access)
        self.s3_client.upload_fileobj(
            buffer,
            self.bucket_name,
            s3_key,
            ExtraArgs={'ContentType': 'image/jpeg'}
        )
        
        # Return public URL
        return f"{self.get_base_url()}/{s3_key}"
    
    def save_file(self, file_obj, filename: str) -> str:
        """
        Save raw file object and return URL or path
        
        Args:
            file_obj: File-like object (must support read/seek)
            filename: Target filename
            
        Returns:
            URL (S3) or path (local)
        """
        if self.storage_type == "s3":
            return self._save_file_to_s3(file_obj, filename)
        else:
            return self._save_file_to_local(file_obj, filename)

    def _save_file_to_local(self, file_obj, filename: str) -> str:
        """Save raw file to local filesystem"""
        # Ensure directory exists
        file_path = os.path.join(self.items_path, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        file_obj.seek(0)
        with open(file_path, 'wb') as f:
            f.write(file_obj.read())
        
        return file_path

    def _save_file_to_s3(self, file_obj, filename: str) -> str:
        """Upload raw file to S3"""
        s3_key = f"{self.user_id}/{filename}"
        
        file_obj.seek(0)
        
        # Upload to S3
        self.s3_client.upload_fileobj(
            file_obj,
            self.bucket_name,
            s3_key
        )
        
        # Return public URL
        return f"{self.get_base_url()}/{s3_key}"

    def load_file(self, url_or_path: str) -> Optional[bytes]:
        """
        Load raw file content from URL (S3) or path (local)
        
        Args:
            url_or_path: URL (S3) or local file path
            
        Returns:
            bytes or None if not found
        """
        try:
            if self.storage_type == "s3" and url_or_path.startswith("http"):
                return self._load_file_from_s3(url_or_path)
            else:
                return self._load_file_from_local(url_or_path)
        except Exception as e:
            print(f"Error loading file {url_or_path}: {e}")
            return None

    def _load_file_from_local(self, file_path: str) -> bytes:
        """Load raw file from local filesystem"""
        with open(file_path, 'rb') as f:
            return f.read()

    def _load_file_from_s3(self, url: str) -> bytes:
        """Download raw file from S3"""
        # Extract S3 key from URL
        s3_key = url.replace(f"{self.get_base_url()}/", "")
        
        # Download from S3
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
        return response['Body'].read()

    def delete_file(self, url_or_path: str) -> bool:
        """
        Delete file from storage
        
        Args:
            url_or_path: URL (S3) or local file path
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.storage_type == "s3" and url_or_path.startswith("http"):
                return self._delete_file_from_s3(url_or_path)
            else:
                return self._delete_file_from_local(url_or_path)
        except Exception as e:
            print(f"Error deleting file {url_or_path}: {e}")
            return False

    def _delete_file_from_local(self, file_path: str) -> bool:
        """Delete file from local filesystem"""
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    def _delete_file_from_s3(self, url: str) -> bool:
        """Delete file from S3"""
        # Extract S3 key from URL
        s3_key = url.replace(f"{self.get_base_url()}/", "")
        
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
        return True

        """
        Load image from URL (S3) or path (local)
        
        Args:
            url_or_path: URL (S3) or local file path
            
        Returns:
            PIL Image object or None if not found
        """
        try:
            if self.storage_type == "s3" and url_or_path.startswith("http"):
                return self._load_from_s3(url_or_path)
            else:
                return self._load_from_local(url_or_path)
        except Exception as e:
            print(f"Error loading image {url_or_path}: {e}")
            return None
    
    def _load_from_local(self, file_path: str) -> Image.Image:
        """Load image from local filesystem"""
        return Image.open(file_path)
    
    def _load_from_s3(self, url: str) -> Image.Image:
        """Download and load image from S3"""
        from io import BytesIO
        
        # Extract S3 key from URL
        s3_key = url.replace(f"{self.get_base_url()}/", "")
        
        # Download from S3
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
        image_data = response['Body'].read()
        
        return Image.open(BytesIO(image_data))
    
    def file_exists(self, url_or_path: str) -> bool:
        """Check if file exists"""
        try:
            if self.storage_type == "s3" and url_or_path.startswith("http"):
                return self._s3_file_exists(url_or_path)
            else:
                return os.path.exists(url_or_path)
        except Exception:
            return False
    
    def _s3_file_exists(self, url: str) -> bool:
        """Check if file exists in S3"""
        s3_key = url.replace(f"{self.get_base_url()}/", "")
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except Exception:
            return False
    
    def save_json(self, data: Dict, filename: str) -> None:
        """Save JSON metadata"""
        if self.storage_type == "s3":
            self._save_json_to_s3(data, filename)
        else:
            self._save_json_to_local(data, filename)
    
    def _save_json_to_local(self, data: Dict, filename: str) -> None:
        """Save JSON to local filesystem"""
        file_path = os.path.join(self.base_path, filename)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_json_to_s3(self, data: Dict, filename: str) -> None:
        """Upload JSON to S3"""
        s3_key = f"{self.user_id}/{filename}"
        json_data = json.dumps(data, indent=2).encode('utf-8')
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_data,
                ContentType='application/json'
            )
            print(f"✅ Successfully saved {filename} to S3: {s3_key}")
        except Exception as e:
            print(f"❌ Error saving JSON to S3 ({s3_key}): {e}")
            raise
    
    def load_json(self, filename: str) -> Dict:
        """Load JSON metadata"""
        if self.storage_type == "s3":
            return self._load_json_from_s3(filename)
        else:
            return self._load_json_from_local(filename)
    
    def _load_json_from_local(self, filename: str) -> Dict:
        """Load JSON from local filesystem"""
        file_path = os.path.join(self.base_path, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return {"items": [], "schema_version": "2.0", "last_updated": None}
    
    def _load_json_from_s3(self, filename: str) -> Dict:
        """Download and load JSON from S3"""
        s3_key = f"{self.user_id}/{filename}"
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            data = response['Body'].read().decode('utf-8')
            return json.loads(data)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                # File doesn't exist - return default structure
                return {"items": [], "schema_version": "2.0", "last_updated": None}
            # Other S3 errors - log and return default
            print(f"⚠️ Error loading JSON from S3 ({s3_key}): {e}")
            return {"items": [], "schema_version": "2.0", "last_updated": None}
        except Exception as e:
            # Log the actual error for debugging
            print(f"⚠️ Unexpected error loading JSON from S3 ({s3_key}): {e}")
            return {"items": [], "schema_version": "2.0", "last_updated": None}

