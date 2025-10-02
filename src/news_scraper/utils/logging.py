"""Logging configuration and utilities."""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from news_scraper.config.settings import settings_instance as settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> None:
    """Setup logging configuration for both console and rotating file sinks.
    
    Args:
        log_level: Logging level (defaults to settings.log_level)
        log_file: Log file path (defaults to settings.log_file)
        log_format: Log format (defaults to settings.log_format)

    Returns:
        None: The configuration is applied as a side effect to the global logger.
    """
    # Use settings defaults if not provided
    log_level = log_level or settings.log_level
    log_file = log_file or settings.log_file
    log_format = log_format or settings.log_format
    
    # Remove default handler
    logger.remove()
    
    # Add console handler with colors
    logger.add(
        sys.stderr,
        level=log_level,
        format=log_format,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Add file handler with rotation
    logger.add(
        log_file,
        level=log_level,
        format=log_format,
        rotation=settings.log_max_size,
        retention=settings.log_backup_count,
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    logger.debug(f"Logging initialized - Level: {log_level}, File: {log_file}")


def get_logger(name: str):
    """Get a logger instance with the given name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logger.bind(name=name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self):
        """Get logger for this class.

        Returns:
            loguru.Logger: Child logger bound to the class name.
        """
        return logger.bind(name=self.__class__.__name__)


# Auto-setup logging when module is imported
setup_logging()