import logging

logger = logging.getLogger(__name__)

level = logging.INFO

formatter = logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger.setLevel(level)

console_handler = logging.StreamHandler()
console_handler.setLevel(level)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)