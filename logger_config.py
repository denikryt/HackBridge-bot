import logging
import logging.handlers
import os

def setup_logging():
    """Setup simple logging with rotating file handler (64MB splits)"""
    
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
    
    # File handler with 64MB rotation
    file_handler = logging.handlers.RotatingFileHandler(
        "logs/bot.log",
        maxBytes=64 * 1024 * 1024,  # 64MB
        backupCount=5,
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
    
    logging.info("Logging initialized - files will rotate at 64MB")

def get_logger(name):
    """Get a logger instance"""
    return logging.getLogger(name)
