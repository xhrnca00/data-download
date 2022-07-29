import logging

from typing import Dict, Union

from . import defaults

ENABLE_CMD_PRINTING = True

if ENABLE_CMD_PRINTING:
    try:
        # zdroj: https://stackoverflow.com/q/36760127/1047788
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except AttributeError:
        pass


class LoggingFormatter(logging.Formatter):
    reset = "\x1b[0m"
    red = "\x1b[31;1m"
    green = "\x1b[32;1m"
    yellow = "\x1b[33;1m"
    blue = "\x1b[34;1m"
    white = "\x1b[37;1m"

    FORMATS: Dict[Union[int, str], str] = {}

    def __init__(self) -> None:
        super().__init__()
        self._add_level(logging.DEBUG, self.white)
        self._add_level(logging.SUCCESS, self.green)
        self._add_level(logging.INFO, self.blue)
        self._add_level(logging.WARNING, self.yellow)
        self._add_level(logging.ERROR, self.red)
        self._add_level(logging.FATAL, self.red)

    def _add_level(self, level, color):
        self.FORMATS[level] = color + \
            "%(levelname)s" + self.reset + ": %(message)s"

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# for type annotation
class Logger(logging.Logger):
    def success(self, msg: object, *args, **kwargs):
        """
        Has same args as other logging objects (see logging.debug for example).
        """


# ENHANCE: add an "important" or "highlight" or sth like that level

# set success level
logging.SUCCESS = 25  # between WARNING and INFO
logging.addLevelName(logging.SUCCESS, 'SUCCESS')


def _init_logger(name: str) -> Logger:
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setFormatter(LoggingFormatter())
    logger.addHandler(handler)
    setattr(logger, 'success', lambda message,
            *args: logger._log(logging.SUCCESS, message, args))
    logger.setLevel(defaults.LOG_LEVEL)
    # log the log level to debug
    # // logger.debug("Initialized logger" + " " +
    # //              f"{name}" + " " +
    # //              f"with level {logger.getEffectiveLevel()}")
    return logger


def get_logger() -> Logger:
    try:
        return get_logger.logger
    except AttributeError:
        # only one logger for now, we can print filepaths instead
        get_logger.logger = _init_logger("LOGGER")
        return get_logger.logger
