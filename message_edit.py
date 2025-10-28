import discord
import helpers
import database
from logger_config import get_logger

logger = get_logger(__name__)

async def handle_message_edit(bot, before: discord.Message, after: discord.Message):
    """Handles edited messages and updates all linked messages."""
    
    # Ignore edits from the bot itself
    if after.author == bot.user:
        return
    
    # Ignore edits from webhooks
    if after.webhook_id:
        return
    
    # Only handle edits if the content actually changed
    if before.content == after.content:
        return
    
    # Ignore if the edited message has no content (e.g., only embeds)
    if not after.content and not before.content:
        return
    
    logger.info(f"Handling message edit from {after.author} in {after.guild.name}#{after.channel.name}")
    
    # Check if the edited message is in a thread
    if isinstance(after.channel, discord.Thread):
        await handle_thread_message_edit(bot, before, after)
    else:
        await handle_channel_message_edit(bot, before, after)

async def handle_channel_message_edit(bot, before: discord.Message, after: discord.Message):
    """Handles edited messages in regular channels and updates all linked messages."""
    
    channel_id = str(after.channel.id)
    target_channel_ids = helpers.find_linked_channels(channel_id)
    
    if target_channel_ids is None:
        logger.debug(f"No linked channels found for channel {channel_id}")
        return
    
    # Find the message group entry for the edited message
    group_name = helpers.get_group_name(channel_id)
    message_entry = database.get_message_group_entry_by_message_id(after.id, group_name)
    
    if not message_entry:
        logger.warning(f"No message group entry found for edited message {after.id}")
        return
    
    logger.info(f"Updating edited message in {len(target_channel_ids)} linked channels")
    
    # Form new header and content for the edited message
    guild_name = after.guild.name if after.guild else "Unknown Guild"
    header = helpers.form_header(after, guild_name, len(target_channel_ids))
    new_msg = helpers.form_message_text(header, after.content)
    
    edited_count = 0
    # Update the message in each linked channel
    for entry in message_entry:
        # Skip the original message entry
        if entry["guild_id"] == helpers.get_guild_id_from_channel_id(channel_id) and entry["channel_id"] == channel_id:
            continue
            
        target_channel = bot.get_channel(int(entry["channel_id"]))
        if target_channel:
            try:
                # Fetch the linked message and edit it
                linked_message = await target_channel.fetch_message(int(entry["message_id"]))
                await linked_message.edit(content=new_msg)
                edited_count += 1
                logger.debug(f"Updated message in {target_channel.guild.name}#{target_channel.name}")
            except discord.NotFound:
                logger.warning(f"Linked message {entry['message_id']} not found in {target_channel.guild.name}#{target_channel.name}")
            except discord.Forbidden:
                logger.error(f"No permission to edit message in {target_channel.guild.name}#{target_channel.name}")
            except Exception as e:
                logger.error(f"Failed to edit message in {target_channel.guild.name}#{target_channel.name}: {e}")
        else:
            logger.error(f"Target channel with ID {entry['channel_id']} not found")
    
    logger.info(f"Successfully updated {edited_count} linked messages")

async def handle_thread_message_edit(bot, before: discord.Message, after: discord.Message):
    """Handles edited messages in threads and updates all linked messages."""
    
    parent_channel_id = str(after.channel.parent_id)
    target_channel_ids = helpers.find_linked_channels(parent_channel_id)
    
    if target_channel_ids is None:
        logger.debug(f"No linked channels found for parent channel {parent_channel_id}")
        return
    
    # Find the message group entry for the edited message
    group_name = helpers.get_group_name(parent_channel_id)
    message_entry = database.get_message_group_entry_by_message_id(after.id, group_name)
    
    if not message_entry:
        logger.warning(f"No message group entry found for edited thread message {after.id}")
        return
    
    logger.info(f"Updating edited thread message in {len(target_channel_ids)} linked channels")
    
    # Form new header and content for the edited message
    guild_name = after.guild.name if after.guild else "Unknown Guild"
    header = helpers.form_header(after, guild_name, len(target_channel_ids))
    new_msg = helpers.form_message_text(header, after.content)

    edited_count = 0
    # Update the message in each linked thread
    for entry in message_entry:
        # Skip the original message entry
        if (entry["guild_id"] == helpers.get_guild_id_from_channel_id(parent_channel_id) and 
            entry["channel_id"] == parent_channel_id and 
            entry.get("thread_id") == str(after.channel.id)):
            continue
        
        target_channel = bot.get_channel(int(entry["channel_id"]))
        if target_channel and "thread_id" in entry:
            try:
                # Get the parent message to access the thread
                parent_message = await target_channel.fetch_message(int(entry["thread_id"]))
                if parent_message.thread:
                    # Fetch the linked message in the thread and edit it
                    linked_message = await parent_message.thread.fetch_message(int(entry["message_id"]))
                    await linked_message.edit(content=new_msg)
                    edited_count += 1
                    logger.debug(f"Updated thread message in {target_channel.guild.name}#{target_channel.name}")
                else:
                    logger.warning(f"Thread not found for parent message {entry['thread_id']}")
            except discord.NotFound:
                logger.warning(f"Linked thread message {entry['message_id']} not found")
            except discord.Forbidden:
                logger.error(f"No permission to edit thread message in {target_channel.guild.name}#{target_channel.name}")
            except Exception as e:
                logger.error(f"Failed to edit thread message in {target_channel.guild.name}#{target_channel.name}: {e}")
        else:
            logger.error(f"Target channel with ID {entry['channel_id']} not found or no thread_id in entry")
    
    logger.info(f"Successfully updated {edited_count} linked thread messages")