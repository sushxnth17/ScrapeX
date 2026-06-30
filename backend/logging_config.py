"""Central logging configuration module for ScrapeX."""

import logging
import sys

def configure_logging(level=logging.INFO):
    """Configure standard stdout logging for all ScrapeX components."""
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Check if handler already exists to prevent duplicate logging
    if not root_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
