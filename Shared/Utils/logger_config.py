import logging
import os
import sys


def setup_logger(name=__name__):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        short_name = os.path.basename(name)  # just show filename, not full module path
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
            # Or: f'%(asctime)s - {short_name} - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
