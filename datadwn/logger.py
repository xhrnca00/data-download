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
    dark_black = "\x1b[30m"
    bright_black = "\x1b[30;1m"
    dark_red = "\x1b[31m"
    bright_red = "\x1b[31;1m"
    dark_green = "\x1b[32m"
    bright_green = "\x1b[32;1m"
    dark_yellow = "\x1b[33m"
    bright_yellow = "\x1b[33;1m"
    dark_blue = "\x1b[34m"
    bright_blue = "\x1b[34;1m"
    dark_magenta = "\x1b[35m"
    bright_magenta = "\x1b[35;1m"
    dark_cyan = "\x1b[36m"
    bright_cyan = "\x1b[36;1m"
    dark_white = "\x1b[37m"
    bright_white = "\x1b[37;1m"

    FORMATS: Dict[Union[int, str], str] = {}

    def __init__(self) -> None:
        super().__init__()
        self._add_level(logging.DEBUG, self.bright_white)
        self._add_level(logging.SUCCESS, self.bright_magenta)
        self._add_level(logging.INFO, self.bright_blue)
        self._add_level(logging.WARNING, self.bright_yellow)
        self._add_level(logging.IMPORTANT, self.bright_magenta)
        self._add_level(logging.ERROR, self.bright_red)
        self._add_level(logging.CRITICAL, self.dark_red)

    def _add_level(self, level, color):
        self.FORMATS[level] = color + \
            "%(levelname)s" + self.reset + ": %(message)s"

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

    @classmethod
    def print_colors(cls):
        print(f"some text\n{cls.reset}".join([
            cls.dark_black,  cls.bright_black, cls.dark_red, cls.bright_red,
            cls.dark_green,  cls.bright_green, cls.dark_yellow, cls.bright_yellow,
            cls.dark_blue, cls.bright_blue, cls.dark_magenta,  cls.bright_magenta,
            cls.dark_cyan, cls.bright_cyan, cls.dark_white, cls.bright_white, cls.reset]))


# for type annotation
class Logger(logging.Logger):
    def success(self, msg: object, *args, **kwargs):
        """
        Has same args as other logging objects (see logging.debug for example).
        """

    def important(self, msg: object, *args, **kwargs):
        """
        Has same args as other logging objects (see logging.debug for example).
        """

#! remove this when developing
# mypy: ignore-errors


# set success level
logging.SUCCESS = 25  # between WARNING and INFO
logging.addLevelName(logging.SUCCESS, 'SUCCESS')
logging.IMPORTANT = 35
logging.addLevelName(logging.IMPORTANT, "IMPORTANT")


def _init_logger(name: str) -> Logger:
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setFormatter(LoggingFormatter())
    logger.addHandler(handler)
    setattr(logger, 'success', lambda message,
            *args: logger._log(logging.SUCCESS, message, args))
    setattr(logger, 'important', lambda message,
            *args: logger._log(logging.IMPORTANT, message, args))
    logger.setLevel(defaults.LOG_LEVEL)
    # log the log level to debug
    # // logger.debug("Initialized logger" + " " +
    # //              f"{name}" + " " +
    # //              f"with level {logger.getEffectiveLevel()}")
    return logger  # NOSONAR


def get_logger() -> Logger:
    try:
        return get_logger.logger
    except AttributeError:
        # only one logger for now, we can print filepaths instead
        get_logger.logger = _init_logger("LOGGER")
        return get_logger.logger
