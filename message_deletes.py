import discord
import helpers
import database
from logger_config import get_logger

logger = get_logger(__name__)

async def handle_message_delete(bot, message: discord.Message):
    """Handles deleted messages and deletes all linked messages."""
    
    # Ignore deletions of messages from the bot itself
    if message.author == bot.user:
        return
    
    # Ignore deletions of messages from webhooks
    if message.webhook_id:
        return
    
    logger.info(f"Handling message deletion from {message.author} in {message.guild.name}#{message.channel.name}")
    
    # Check if the deleted message is in a thread
    if isinstance(message.channel, discord.Thread):
        await handle_thread_message_delete(bot, message)
    else:
        await handle_channel_message_delete(bot, message)

async def handle_channel_message_delete(bot, message: discord.Message):
    """Handles deleted messages in regular channels and deletes all linked messages."""
    
    channel_id = str(message.channel.id)
    target_channel_ids = helpers.find_linked_channels(channel_id)
    
    if target_channel_ids is None:
        logger.debug(f"No linked channels found for channel {channel_id}")
        return
    
    # Find the message group entry for the deleted message
    group_name = helpers.get_group_name(channel_id)
    message_entry = database.get_message_group_entry_by_message_id(message.id, group_name)
    
    if not message_entry:
        logger.warning(f"No message group entry found for deleted message {message.id}")
        return
    
    logger.info(f"Deleting linked messages in {len(target_channel_ids)} linked channels")
    
    deleted_count = 0
    # Delete the message in each linked channel
    for entry in message_entry:
        # Skip the original message entry (already deleted)
        if entry["guild_id"] == helpers.get_guild_id_from_channel_id(channel_id) and entry["channel_id"] == channel_id:
            continue
            
        target_channel = bot.get_channel(int(entry["channel_id"]))
        if target_channel:
            try:
                # Fetch the linked message and delete it
                linked_message = await target_channel.fetch_message(int(entry["message_id"]))
                await linked_message.delete()
                deleted_count += 1
                logger.debug(f"Deleted message in {target_channel.guild.name}#{target_channel.name}")
            except discord.NotFound:
                logger.warning(f"Linked message {entry['message_id']} already deleted or not found in {target_channel.guild.name}#{target_channel.name}")
            except discord.Forbidden:
                logger.error(f"No permission to delete message in {target_channel.guild.name}#{target_channel.name}")
            except Exception as e:
                logger.error(f"Failed to delete message in {target_channel.guild.name}#{target_channel.name}: {e}")
        else:
            logger.error(f"Target channel with ID {entry['channel_id']} not found")
    
    # Remove the message group entry from the database
    try:
        database.delete_message_group_entry_by_message_id(message.id, group_name)
        logger.debug(f"Removed message group entry for deleted message {message.id}")
    except Exception as e:
        logger.error(f"Failed to remove message group entry: {e}")
    
    logger.info(f"Successfully deleted {deleted_count} linked messages")

async def handle_thread_message_delete(bot, message: discord.Message):
    """Handles deleted messages in threads and deletes all linked messages."""
    
    parent_channel_id = str(message.channel.parent_id)
    target_channel_ids = helpers.find_linked_channels(parent_channel_id)
    
    if target_channel_ids is None:
        logger.debug(f"No linked channels found for parent channel {parent_channel_id}")
        return
    
    # Find the message group entry for the deleted message
    group_name = helpers.get_group_name(parent_channel_id)
    message_entry = database.get_message_group_entry_by_message_id(message.id, group_name)
    
    if not message_entry:
        logger.warning(f"No message group entry found for deleted thread message {message.id}")
        return
    
    logger.info(f"Deleting linked thread messages in {len(target_channel_ids)} linked channels")
    
    deleted_count = 0
    # Delete the message in each linked thread
    for entry in message_entry:
        # Skip the original message entry (already deleted)
        if (entry["guild_id"] == helpers.get_guild_id_from_channel_id(parent_channel_id) and 
            entry["channel_id"] == parent_channel_id and 
            entry.get("thread_id") == str(message.channel.id)):
            continue
        
        target_channel = bot.get_channel(int(entry["channel_id"]))
        if target_channel and "thread_id" in entry:
            try:
                # Get the parent message to access the thread
                parent_message = await target_channel.fetch_message(int(entry["thread_id"]))
                if parent_message.thread:
                    # Fetch the linked message in the thread and delete it
                    linked_message = await parent_message.thread.fetch_message(int(entry["message_id"]))
                    await linked_message.delete()
                    deleted_count += 1
                    logger.debug(f"Deleted thread message in {target_channel.guild.name}#{target_channel.name}")
                else:
                    logger.warning(f"Thread not found for parent message {entry['thread_id']}")
            except discord.NotFound:
                logger.warning(f"Linked thread message {entry['message_id']} already deleted or not found")
            except discord.Forbidden:
                logger.error(f"No permission to delete thread message in {target_channel.guild.name}#{target_channel.name}")
            except Exception as e:
                logger.error(f"Failed to delete thread message in {target_channel.guild.name}#{target_channel.name}: {e}")
        else:
            logger.error(f"Target channel with ID {entry['channel_id']} not found or no thread_id in entry")
    
    # Remove the message group entry from the database
    try:
        database.delete_message_group_entry_by_message_id(message.id, group_name)
        logger.debug(f"Removed message group entry for deleted thread message {message.id}")
    except Exception as e:
        logger.error(f"Failed to remove message group entry: {e}")
    
    logger.info(f"Successfully deleted {deleted_count} linked thread messages")
