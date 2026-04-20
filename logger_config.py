import logging
import logging.handlers
import os

def setup_logging():
    """Setup logging that overwrites logs/bot.log on each run and mirrors to console."""
    
    log_file = os.environ.get("LOG_FILE", "logs/bot.log")
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    level = logging.DEBUG
    
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
        log_file,
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
    
    logging.info("Logging initialized - log file %s will be overwritten on each run", log_file)

def get_logger(name):
    """Get a logger instance"""
    return logging.getLogger(name)
