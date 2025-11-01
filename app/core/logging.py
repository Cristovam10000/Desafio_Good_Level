"""
Structured logging configuration following Clean Code principles.
Replaces print statements with proper logging throughout the application.
"""

import logging
import sys
from typing import Optional

from app.core.config import settings


class StructuredLogger:
    """Structured logger with consistent formatting and levels."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def debug(self, message: str, **kwargs):
        """Log debug message with structured data."""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """Log info message with structured data."""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with structured data."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, exc: Optional[Exception] = None, **kwargs):
        """Log error message with structured data."""
        if exc:
            self.logger.error(message, exc_info=exc, extra=kwargs)
        else:
            self.logger.error(message, extra=kwargs)

    def critical(self, message: str, exc: Optional[Exception] = None, **kwargs):
        """Log critical message with structured data."""
        if exc:
            self.logger.critical(message, exc_info=exc, extra=kwargs)
        else:
            self.logger.critical(message, extra=kwargs)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging output."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data."""
        # Add timestamp if not present
        if not hasattr(record, 'timestamp'):
            record.timestamp = self.formatTime(record, self.default_time_format)

        # Base format
        base_format = f"[{record.timestamp}] {record.levelname} {record.name}: {record.getMessage()}"

        # Add extra fields if present
        extra_fields = []
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                             'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                             'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                             'thread', 'threadName', 'processName', 'process', 'message',
                             'timestamp']:
                    extra_fields.append(f"{key}={value}")

        if extra_fields:
            return f"{base_format} | {' | '.join(extra_fields)}"

        return base_format


def configure_logging(
    level: str = "INFO",
    format_type: str = "structured",
    enable_console: bool = True,
    enable_file: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure application-wide logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ('structured' or 'simple')
        enable_console: Enable console logging
        enable_file: Enable file logging
        log_file: Log file path (required if enable_file=True)
    """
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Create formatter
    if format_type == "structured":
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if enable_file and log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance for the given name."""
    return StructuredLogger(name)


# Global logger instances for common use
app_logger = get_logger("app")
auth_logger = get_logger("auth")
db_logger = get_logger("db")
api_logger = get_logger("api")


def init_app_logging():
    """Initialize application logging based on settings."""
    log_config = {
        "level": settings.LOG_LEVEL if hasattr(settings, "LOG_LEVEL") else "INFO",
        "format_type": "structured",
        "enable_console": True,
        "enable_file": getattr(settings, "LOG_TO_FILE", False),
        "log_file": getattr(settings, "LOG_FILE_PATH", None),
    }

    configure_logging(**log_config)
    app_logger.info("Application logging initialized", **log_config)