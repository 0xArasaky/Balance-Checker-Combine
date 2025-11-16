import sys
from pathlib import Path
from loguru import logger

LOG_LEVEL = "INFO"
LOG_TO_FILE = True
LOG_FILE_FORMAT = "app_{time:YYYY-MM-DD}.log"
LOG_ROTATION = "1 day"
LOG_RETENTION = "7 days"
LOG_COMPRESSION = "zip"
LOG_MODULE_NAME_WIDTH = 38

_logging_setup_done = False


def setup_logging():
    global _logging_setup_done

    if _logging_setup_done:
        return

    logger.remove()

    logger.add(
        sys.stdout,
        level=LOG_LEVEL,
        format=f"<green>{{time:DD.MM.YYYY HH:mm:ss}}</green> | <level>{{level: <8}}</level> | <cyan>{{name: <{LOG_MODULE_NAME_WIDTH}}}</cyan> | {{message}}",
        colorize=True
    )

    if LOG_TO_FILE:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        logger.add(
            log_dir / LOG_FILE_FORMAT,
            level="DEBUG",
            format=f"{{time:YYYY-MM-DD HH:mm:ss}} | {{level: <8}} | {{name: <{LOG_MODULE_NAME_WIDTH}}} | {{message}}",
            rotation=LOG_ROTATION,
            retention=LOG_RETENTION,
            compression=LOG_COMPRESSION,
            encoding="utf-8"
        )

    _logging_setup_done = True


def error_log(message: str) -> None:
    logger.opt(colors=True, depth=1).error(f"<red>{message}</red>")


def warning_log(message: str) -> None:
    logger.opt(colors=True, depth=1).warning(f"<yellow>{message}</yellow>")


def success_log(message: str) -> None:
    logger.opt(colors=True, depth=1).success(f"<green>{message}</green>")


def info_log(message: str) -> None:
    logger.opt(depth=1).info(message)


def debug_log(message: str) -> None:
    logger.opt(depth=1).debug(message)
