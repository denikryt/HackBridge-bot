import logging
import logging.handlers
import os

def setup_logging():
    """Setup simple logging that overwrites log file on each run"""
    
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    # Basic formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    # Root logger setup
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    # File handler that overwrites on each run
    file_handler = logging.FileHandler(
        "logs/bot.log",
        mode='w',  # Overwrite mode
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Suppress discord.py debug messages
    logging.getLogger('discord').setLevel(logging.WARNING)
    
    logging.info("Logging initialized - log file will be overwritten on each run")

def get_logger(name):
    """Get a logger instance"""
    return logging.getLogger(name)
