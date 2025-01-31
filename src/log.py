import logging
import colorlog
logger = colorlog.getLogger("Argus")
# Configure logging
logger.setLevel( logging.INFO)
formatter = colorlog.ColoredFormatter('%(log_color)s%(asctime)s - %(levelname)s: %(message)s', datefmt="%Y-%m-%d %H:%M")
console_handler = logging.StreamHandler()
console_handler.setLevel( logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

