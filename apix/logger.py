"""Module handling internal and dependency logging."""
import sys

from loguru import logger
import urllib3


def setup_loguru(level="info", path="logs/apix.log"):
    logger.remove()
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | " "{level: <8} | " "{name}:{function}:{line} - {message}"
    )
    logger.add(
        sys.stderr,
        level=level.upper(),
        format=console_format,
    )
    logger.add(
        path,
        level=level.upper(),
        rotation="10 MB",
        retention="3 days",
        format=file_format,
    )


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
setup_loguru()
