from dotenv import load_dotenv
import os
from typing import List


def empty_to_none(field):
    value = os.getenv(field)
    if value is None or len(value) == 0:
        return None
    return value


class Secrets:
    service_secret: str
    google_client_id: str
    google_client_secret: str
    minio_access_key: str
    minio_secret_key: str

    def __init__(self):
        self.service_secret = os.getenv("SERVICE_SECRET")
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY")

        # Load the environment variables
        load_dotenv()

# TODO: getopt() for cmd line arguments
class Config:
    host_name: str
    listen_address: str
    listen_port: int
    minio_endpoint: str
    minio_bucket: str
    database_path: str
    debug: bool
    log_path: str | None

    secrets: Secrets

    def __init__(self):
        # Load the environment variables
        load_dotenv()

        self.host_name = os.getenv("HOST_NAME", "http://localhost:9000")

        self.listen_address = os.getenv("LISTEN_ADDRESS", "0.0.0.0")

        self.listen_port = int(os.getenv("LISTEN_PORT", 8000))

        self.database_path = os.getenv("DATABASE_PATH", ":memory:")
        
        self.minio_endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")

        # Set the log path
        self.log_path = empty_to_none("LOG_PATH")

        # Determine if the DEBUG mode is set
        debug = os.getenv("DEBUG", "True")
        self.debug = debug == "True"

        self.secrets = Secrets()
