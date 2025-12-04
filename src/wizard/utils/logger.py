import logging
from rich.logging import RichHandler


logging.basicConfig(
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(rich_tracebacks=True, markup=True),
        logging.FileHandler("wizard.log"),
    ],
)


def get_logger(
    name: str = __package__,
    level: int = logging.INFO,
    file: str = __package__ + ".log",
    console: bool = True,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    # Console handler for rich logging
    if console:
        console_handler = RichHandler(markup=True)
        logger.addHandler(console_handler)

    # File handler for append-only logging
    file_handler = logging.FileHandler(file, mode="a")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger
