import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent
LOG_DIR = BACKEND_ROOT / 'logs'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'


def get_backend_logger(name, filename, level=logging.INFO):
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    log_path = LOG_DIR / filename
    if any(
        isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename) == log_path
        for handler in logger.handlers
    ):
        return logger

    handler = RotatingFileHandler(
        log_path,
        maxBytes=1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)

    return logger
