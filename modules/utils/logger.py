"""
Модуль логирования для Balance Checker
Использует loguru для красивого и информативного вывода
"""

import sys
from pathlib import Path
from loguru import logger

# Настройки логирования
LOG_LEVEL = "INFO"
LOG_TO_FILE = True
LOG_FILE_FORMAT = "app_{time:YYYY-MM-DD}.log"
LOG_ROTATION = "1 day"
LOG_RETENTION = "7 days"
LOG_COMPRESSION = "zip"
LOG_MODULE_NAME_WIDTH = 38

# Флаг чтобы избежать повторной настройки
_logging_setup_done = False


def setup_logging():
    """Настройка системы логирования"""
    global _logging_setup_done

    if _logging_setup_done:
        return

    # Удаляем стандартный обработчик
    logger.remove()

    # Консольный вывод с цветами
    logger.add(
        sys.stdout,
        level=LOG_LEVEL,
        format=f"<green>{{time:DD.MM.YYYY HH:mm:ss}}</green> | <level>{{level: <8}}</level> | <cyan>{{name: <{LOG_MODULE_NAME_WIDTH}}}</cyan> | {{message}}",
        colorize=True
    )

    # Файловый вывод
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


# Функция экранирования угловых скобок для loguru
def _escape_tags(message: str) -> str:
    """Экранирует угловые скобки чтобы loguru не интерпретировал их как цветовые теги"""
    return message.replace("<", r"\<").replace(">", r"\>")


# Специализированные функции логирования
def error_log(message: str) -> None:
    """Логирование ошибок с красным цветом"""
    escaped = _escape_tags(message)
    logger.opt(colors=True, depth=1).error(f"<red>{escaped}</red>")


def warning_log(message: str) -> None:
    """Логирование предупреждений с желтым цветом"""
    escaped = _escape_tags(message)
    logger.opt(colors=True, depth=1).warning(f"<yellow>{escaped}</yellow>")


def success_log(message: str) -> None:
    """Логирование успешных операций с зеленым цветом"""
    escaped = _escape_tags(message)
    logger.opt(colors=True, depth=1).success(f"<green>{escaped}</green>")


def info_log(message: str) -> None:
    """Информационное логирование"""
    escaped = _escape_tags(message)
    logger.opt(depth=1).info(escaped)


def debug_log(message: str) -> None:
    """Отладочное логирование"""
    escaped = _escape_tags(message)
    logger.opt(depth=1).debug(escaped)
