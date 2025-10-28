import discord
from logger_config import get_logger
import message_send
import message_forward

logger = get_logger(__name__)

class MessageWorker:
    def __init__(self, bot):
        self.bot = bot

    def _should_ignore_message(self, message: discord.Message) -> bool:
        """
        Check if the message should be ignored based on various criteria.
        """
        # Ignore messages from the bot itself
        if message.author == self.bot.user:
            return True
        
        # Ignore messages from webhooks
        if message.webhook_id:
            return True

        # Ignore empty thread creation messages
        if isinstance(message.channel, discord.Thread) and not message.content:
            return True

        return False

    async def process_message(self, message: discord.Message):
        """
        Main entry point for processing messages. Routes messages to appropriate handlers
        based on their type (regular, reply, thread, reply in thread).
        """
        if self._should_ignore_message(message):
            return

        try:
            if isinstance(message.channel, discord.Thread):
                if message.reference:
                    # Reply in thread
                    logger.info(f"Processing reply in thread from {message.author} in {message.channel.name}")
                    await message_send.handle_reply_message_in_thread(self.bot, message)
                else:
                    # Regular thread message
                    logger.info(f"Processing thread message from {message.author} in {message.channel.name}")
                    await message_send.handle_thread_message(self.bot, message)
            else:
                if message.reference:
                    if message.reference.type == discord.MessageReferenceType.forward:
                        # Forward message
                        logger.info(f"Processing forward message from {message.author} in {message.channel.name}")
                        await message_forward.handle_forward_message(self.bot, message)
                    else:
                        # Reply in regular channel
                        logger.info(f"Processing reply message from {message.author} in {message.channel.name}")
                        await message_send.handle_reply_message_in_channel(self.bot, message)
                else:
                    # Regular message
                    logger.info(f"Processing regular message from {message.author} in {message.channel.name}")
                    await message_send.handle_message(self.bot, message)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)