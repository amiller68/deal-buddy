import logging
import os
from fastapi import Request


# Used to log events that span a request on our server
class RequestFormatter(logging.Formatter):
    def format(self, record):
        if hasattr(record, "method"):
            record.method = record.method
        # Note: this should never happen, but if it does, we'll just set the request method and URL to N/A
        else:
            record.method = "N/A"
        if hasattr(record, "url"):
            record.url = record.url
        # Note: this should never happen, but if it does, we'll just set the request method and URL to N/A
        else:
            record.url = "N/A"
        return super().format(record)


class Logger:
    logger: logging.Logger
    handler: logging.Handler

    def __init__(self, log_path=None, debug=False):
        """
        Initialize a new Log instance
        - log_path - where to send output. If `None` logs are sent to the console
        - debug - whether to set debug level
        """

        # Create the logger
        logger = logging.getLogger(__name__)

        # Set our debug mode
        if debug:
            logging.basicConfig(level=logging.DEBUG)
            # Hide debug logs from other libraries
            logging.getLogger("asyncio").setLevel(logging.WARNING)
            logging.getLogger("aiosqlite").setLevel(logging.WARNING)
        else:
            logging.basicConfig(level=logging.INFO)

        # Set where to send logs
        if log_path is not None and log_path.strip() != "":
            # Create parent directories if they don't exist
            log_path = log_path.strip()
            log_dir = os.path.dirname(log_path)
            os.makedirs(log_dir, exist_ok=True)
            self.handler = logging.FileHandler(log_path)
        else:
            self.handler = logging.StreamHandler()

        if logger.hasHandlers():
            logger.handlers.clear()
        logger.addHandler(self.handler)

        self.logger = logger

    # TODO: be better about this
    def get_worker_logger(self, name: str = None, attempt: int = None):
        formatter = logging.Formatter(
            f"[worker] %(asctime)s - {name} - {attempt} - %(levelname)s - %(message)s"
        )
        self.handler.setFormatter(formatter)
        return self.logger

    def get_request_span(self, request: Request):
        # Set the log formatter
        formatter = RequestFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(method)s - %(url)s"
        )
        self.handler.setFormatter(formatter)
        return RequestSpan(self.logger, request)


class RequestSpan:
    def __init__(self, logger, request: Request):
        self.logger = logger
        self.request = request

    def warn(self, message):
        self.logger.warn(
            message, extra={"method": self.request.method, "url": self.request.url}
        )

    def debug(self, message):
        self.logger.debug(
            message, extra={"method": self.request.method, "url": self.request.url}
        )

    def info(self, message):
        self.logger.info(
            message, extra={"method": self.request.method, "url": self.request.url}
        )

    def error(self, message):
        self.logger.error(
            message, extra={"method": self.request.method, "url": self.request.url}
        )
