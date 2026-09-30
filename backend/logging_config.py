import logging
import sys
from backend.config import settings


class _SecretRedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from backend.security import redact_secrets

            if isinstance(record.msg, str):
                record.msg = redact_secrets(record.msg)
            if record.args:
                record.args = tuple(
                    redact_secrets(a) if isinstance(a, str) else a for a in record.args
                )
        except Exception:
            pass
        return True


def setup_logger(name: str = "ai_student_copilot") -> logging.Logger:
    """Configures and returns a structured logger."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
        handler.addFilter(_SecretRedactFilter())

        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logger()
