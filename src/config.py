from dotenv import load_dotenv
import os


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
    anthropic_api_key: str

    def __init__(self):
        self.service_secret = os.getenv("SERVICE_SECRET")
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        # Load the environment variables
        load_dotenv()


# TODO: getopt() for cmd line arguments
class Config:
    dev_mode: bool
    host_name: str
    listen_address: str
    listen_port: int
    redis_url: str
    minio_endpoint: str
    minio_bucket: str
    database_path: str
    debug: bool
    log_path: str | None

    secrets: Secrets

    def __init__(self):
        # Load the environment variables
        load_dotenv()

        self.dev_mode = os.getenv("DEV_MODE", "False") == "True"

        self.host_name = os.getenv("HOST_NAME", "http://localhost:9000")

        self.listen_address = os.getenv("LISTEN_ADDRESS", "0.0.0.0")

        self.listen_port = int(os.getenv("LISTEN_PORT", 8000))

        self.database_path = os.getenv("DATABASE_PATH", ":memory:")

        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        self.minio_endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")

        # Set the log path
        self.log_path = empty_to_none("LOG_PATH")

        # Determine if the DEBUG mode is set
        debug = os.getenv("DEBUG", "True")
        self.debug = debug == "True"

        self.secrets = Secrets()

    def show(self, deep: bool = False):
        if deep:
            secrets = self.secrets.__dict__
            secrets.pop("service_secret")
            print(self.__dict__)
            print(secrets)
        else:
            print(self.__dict__)
