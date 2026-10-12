import json
import logging
from typing import Any, Dict
from app.core.config import settings

class JSONFormatter(logging.Formatter):
    """
    Custom structured JSON log formatter.
    Ensures standard machine-readable log fields: timestamp, level, message, logger name,
    and optional correlation_id or extra context.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include correlation ID if present on record
        if hasattr(record, "correlation_id") and record.correlation_id:
            log_record["correlation_id"] = record.correlation_id

        # Include exception details if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def setup_logging() -> None:
    """
    Configure application logging based on environment settings.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to prevent duplicate lines
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setLevel(log_level)

    if settings.LOG_JSON_FORMAT:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
            )
        )

    root_logger.addHandler(handler)

    # Silence overly verbose third-party loggers if needed
    logging.getLogger("uvicorn.access").setLevel(log_level)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
