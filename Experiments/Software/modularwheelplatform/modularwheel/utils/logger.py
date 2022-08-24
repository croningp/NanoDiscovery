"""
.. module:: prototools.logger
    :platforms: Unix
    :synopsis: Custom logger with ANSI coloring

.. moduleauthor:: Graham Keenan 2020

"""

# System imports
import time
import logging
from typing import Optional

ANSI_COLORS = {
    'black': '\u001b[30m',
    'red': '\u001b[31m',
    'green': '\u001b[32m',
    'yellow': '\u001b[33m',
    'blue': '\u001b[34m',
    'magenta': '\u001b[35m',
    'cyan': '\u001b[36m',
    'white': '\u001b[37m',
    'bold': '\u001b[1m',
    'reset': '\u001b[0m'
}

def colour_item(
    msg: str, color: Optional[str] = '', bold: Optional[bool] = False
) -> str:
    """Colours a message with an ANSI color and escapes it at the end.
    Options for bold text.

    Args:
        msg (str): Message to colour
        color (str): Colour of the text
        bold (Optional[bool], optional): Bold the message. Defaults to False.

    Returns:
        str: ANSI formatted message
    """

    color = ANSI_COLORS[color] if color in ANSI_COLORS else ''

    return (
        f'{color}{ANSI_COLORS["bold"]}{msg}{ANSI_COLORS["reset"]}' if bold
        else f'{color}{msg}{ANSI_COLORS["reset"]}'
    )

def make_logger(
    name: str, filename: Optional[str] = '', debug: Optional[bool] = False
) -> logging.Logger:
    """Creates a logger using the custom ProtoFormatter with options for
    file output.

    Args:
        name (str): Name of the logger
        filename (Optional[str], optional): Output log file. Defaults to ''.
        debug (Optional[bool], optional): Debug mode. Defaults to False.

    Returns:
        logging.Logger: Logger
    """

    # Get logger and set level
    logger = logging.getLogger(name)
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    # Using file logging, add FileHandler
    if filename:
        fh = logging.FileHandler(filename=filename)
        formatter = logging.Formatter(
            "[%(asctime)s] - %(name)s::%(levelname)s -- %(message)s",
            "%d-%m-%Y|%H:%M:%S"
        )
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # Custom ANSI colour formatter for IO stream
    formatter = ProtoFormatter()

    # Setup stream handler
    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    logger.propagate = False

    return logger


class ProtoFormatter(logging.Formatter):
    """Custom Formatter to support ANSI colouring

    Inherits:
        logging.Formatter: Base Formatter
    """

    def __init__(self):
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """Formats the LogRecord with custom formatting

        Args:
            record (logging.LogRecord): Record to format

        Returns:
            str: Formatted Text
        """

        # Get level and level number
        level, levelno, msg = record.levelname, record.levelno, record.msg

        # Colour level name depending on level severity
        if levelno == logging.DEBUG:
            level = colour_item(level, color='red')
        elif levelno == logging.INFO:
            level = colour_item(level, color='green')
        elif levelno == logging.WARN:
            level = colour_item(level, color='yellow', bold=True)
            msg = colour_item(msg, color='yellow')
        elif levelno == logging.ERROR:
            level = colour_item(level, color='red', bold=True)
            msg = colour_item(msg, color='red', bold=True)
        elif levelno == logging.CRITICAL:
            level = colour_item(level, color='red', bold=True)
            msg = colour_item(msg, color='red')

        # Log the current time
        timestamp = time.strftime('%d-%m-%Y|%H:%M:%S')

        # Colour the logger name
        name = colour_item(record.name, color='cyan')

        # Formatted message
        return f'[{timestamp}] - {name}::{level} -- {msg}'
