import io
from minio import Minio
from minio.error import S3Error
import uuid
from enum import Enum as PyEnum
from urllib.parse import urlparse

from config import Config

class StorageBucket(PyEnum):
    oms = "real-estate-oms"

class StorageExceptionType(PyEnum):
    default = "default"

class StorageException(Exception):
    def __init__(self, type: StorageExceptionType, message: str):
        self.message = message
        self.type = type

    def __str__(self):
        return f"{self.message}"

    @staticmethod
    def from_s3_error(e):
        return StorageException(StorageExceptionType.default, str(e))

class Storage:
    client: Minio

    def __init__(self, config: Config):
        # Parse the endpoint URL
        parsed_url = urlparse(config.minio_endpoint)
        
        # Extract host and port
        host = parsed_url.hostname
        port = parsed_url.port or (80 if parsed_url.scheme == 'http' else 443)
        
        # Set up MinIO client
        self.client = Minio(
            f"{host}:{port}",
            access_key=config.secrets.minio_access_key,
            secret_key=config.secrets.minio_secret_key,
            secure=parsed_url.scheme == 'https'
        )

        # Create buckets if they don't exist
        for bucket in StorageBucket:
            if not self.client.bucket_exists(bucket.value):
                self.client.make_bucket(bucket.value)

    def get_object(
            self,
            bucket: StorageBucket,
            object_name: str,
        ):
        return self.client.get_object(bucket.value, object_name)

    def put_object(
            self, 
            stream,
            stream_len,
            bucket: StorageBucket, 
        ):
        try:
            upload_id = str(uuid.uuid4())
            match bucket:
                case StorageBucket.oms:
                    content_type = "application/pdf"
            self.client.put_object(
                bucket_name=bucket.value, 
                object_name=upload_id, 
                data=stream, 
                length=stream_len,
                content_type=content_type
            )
            return upload_id
        except S3Error as e:
            raise StorageException.from_s3_error(e)
