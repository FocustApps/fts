from logging import Logger, getLogger, Formatter, StreamHandler
import sys
from common.config import get_logging_config


def create_logging() -> Logger:
    logger = getLogger(__name__)
    logger_config = get_logging_config()
    logger.setLevel(logger_config.log_level)
    stream_handler = StreamHandler(sys.stdout)
    log_formatter = Formatter(
        "%(asctime)s [%(processName)s: %(process)d] [%(threadName)s:"
        "%(thread)d] [%(levelname)s] %(name)s: %(message)s"
    )
    stream_handler.setFormatter(log_formatter)
    return logger


if __name__ == "__main__":
    # If this module is run directly, set up the logger
    # This is useful for debugging purposes
    log = create_logging()
    log.debug("Debugging information")
    log.info("Informational message")
    log.warning("Warning message")
    log.error("Error message")
    log.critical("Critical message")
