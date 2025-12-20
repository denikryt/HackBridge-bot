import logging
import logging.handlers
import os

def setup_logging():
    """Setup logging that overwrites logs/bot.log on each run and mirrors to console."""
    
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    # Allow overriding log level via env; default to DEBUG to capture header decisions.
    level_name = os.environ.get("LOG_LEVEL", "DEBUG").upper()
    level = getattr(logging, level_name, logging.DEBUG)
    
    # Basic formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    # Root logger setup
    logger = logging.getLogger()
    logger.setLevel(level)
    logger.handlers.clear()
    
    # File handler that overwrites on each run
    file_handler = logging.FileHandler(
        "logs/bot.log",
        mode='w',  # Overwrite mode
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Suppress discord.py debug messages
    logging.getLogger('discord').setLevel(logging.WARNING)
    # Suppress pymongo debug chatter
    logging.getLogger('pymongo').setLevel(logging.WARNING)
    logging.getLogger('pymongo.pool').setLevel(logging.WARNING)
    logging.getLogger('pymongo.connection').setLevel(logging.WARNING)
    logging.getLogger('pymongo.topology').setLevel(logging.WARNING)
    
    logging.info("Logging initialized - log file will be overwritten on each run")

def get_logger(name):
    """Get a logger instance"""
    return logging.getLogger(name)
