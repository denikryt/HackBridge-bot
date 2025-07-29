import json
import random
import discord
import helpers
import config
import database
import emoji
from logger_config import get_logger

logger = get_logger(__name__)

# Handle incoming messages
async def handle_message(bot, message: discord.Message, from_reply=False):
    """Handles incoming messages and forwards them to linked channels."""

    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Ignore messages from webhooks
    if message.webhook_id:
        return
    
    # Check if the message is in a thread
    if isinstance(message.channel, discord.Thread) and not from_reply:
        print(f"Handling message in thread", message.content)
        await handle_thread_message(bot, message)
        return
    
    # Check if the message is a reply
    if message.reference and not from_reply:
        await handle_reply_message(bot, message)
        return

    # Try to find linked channels
    target_channel_ids = helpers.find_linked_channels(str(message.channel.id))
    if target_channel_ids is None:
        return

    logger.info(f"Forwarding message from {message.author} in {message.guild.name}#{message.channel.name} to {len(target_channel_ids)} linked channels")

    # Form first message entry
    message_group_entry = [{
        "guild_id": helpers.get_guild_id_from_channel_id(str(message.channel.id)),
        "channel_id": str(message.channel.id),
        "message_id": str(message.id)
    }]

    group_name = helpers.get_group_name(str(message.channel.id))
    guild_name = message.guild.name if message.guild else "Unknown Guild"
    # Form header for the message
    header = helpers.form_header(message, guild_name, len(target_channel_ids))
    msg = f"{header}\n{message.content}" if message.content else header

    for target_channel_id in target_channel_ids:
        target_channel = bot.get_channel(int(target_channel_id))
        target_guild_id = helpers.get_guild_id_from_channel_id(target_channel_id)
        if target_channel:
            
           # Send the message to the target channel
            try:
                result = await target_channel.send(
                    content=msg,
                    embed=message.embeds[0] if message.embeds else None,
                    files=[await file.to_file() for file in message.attachments]
                )
                logger.debug(f"Message forwarded to {target_channel.guild.name}#{target_channel.name}")
            except Exception as e:
                logger.error(f"Failed to send message to {target_channel.guild.name}#{target_channel.name}: {e}")
                continue

            # Form message entry for every linked channel
            message_group_entry.append({
                 "guild_id": target_guild_id,
                 "channel_id": target_channel_id,
                 "message_id": str(result.id)
            })

        else:
            logger.error(f"Target channel with ID {target_channel_id} not found")
            return
        
    # Save the message group entry to the database
    group_name = helpers.get_group_name(str(message.channel.id))
    try:
        database.save_message_group_entry(group_name, message_group_entry)
        logger.debug(f"Message group entry saved for group {group_name}")
    except Exception as e:
        logger.error(f"Failed to save message group entry: {e}")

async def handle_thread_message(bot, message: discord.Message):
    """Handles messages in threads and forwards them to linked channels."""

    # Check thread creation event 
    if not message.content:
        return 

    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Ignore messages from webhooks
    if message.webhook_id:
        return
    
    logger.info(f"Handling thread message from {message.author} in thread {message.channel.name}")
    
    # Check if the message is in a thread
    if not isinstance(message.channel, discord.Thread):
        handle_message(bot, message)
        return
    
    # Check if message in thread is a reply
    if message.reference:
        logger.info(f"Message in thread {message.channel.name} is a reply, handling as reply message")
        await handle_reply_message(bot, message)
        return

    # Get the parent channel ID
    parent_channel_id = str(message.channel.parent_id)

    # Try to find linked channels for the parent channel
    target_channel_ids = helpers.find_linked_channels(parent_channel_id)
    if target_channel_ids is None:
        logger.debug(f"No linked channels found for parent channel {parent_channel_id}")
        return
    
    logger.info(f"Forwarding thread message to {len(target_channel_ids)} linked channels")
    
    # Form first message entry
    message_group_entry = [{
        "guild_id": helpers.get_guild_id_from_channel_id(parent_channel_id),
        "channel_id": parent_channel_id,
        "thread_id": str(message.channel.id),
        "message_id": str(message.id)
    }]

    group_name = helpers.get_group_name(parent_channel_id)
    guild_name = message.guild.name if message.guild else "Unknown Guild"
    thread_name = message.channel.name
    
    # Form header for the thread message
    header = helpers.form_header(message, guild_name, len(target_channel_ids))
    msg = f"{header}\n{message.content}" if message.content else f"{header}"

    thread_message_entry = database.get_message_group_entry_by_message_id(message.channel.id, group_name)
    
    for target_channel_id in target_channel_ids:
        target_channel = bot.get_channel(int(target_channel_id))
        target_guild_id = helpers.get_guild_id_from_channel_id(target_channel_id)
        
        if target_channel:
            try:
                for entry in thread_message_entry:
                    if entry["guild_id"] == target_guild_id and entry["channel_id"] == target_channel_id:
                        target_thread_message_id = entry["message_id"]
                        break
                    else:
                        logger.info(f"No entry found for target channel {target_channel_id} in thread message group entry")
                try:
                    parent_message = await target_channel.fetch_message(target_thread_message_id)
                except Exception as e:
                    logger.warning(f"Failed to fetch parent message in {target_channel.guild.name}#{target_channel.name}: {e}")
                    return 
                
                parent_text = parent_message.content
                thread_name = " ".join(parent_text.split()[:5])

                if parent_message.thread:
                    target_thread = parent_message.thread
                    result = await target_thread.send(content=msg)
                else:
                    try:
                        thread = await parent_message.create_thread(
                            name=f"{thread_name}",
                        )
                        result = await thread.send(content=msg)
                    except Exception as e:
                        logger.info(f"Error while creating a new thread: {e}")
                        target_thread = parent_message.thread
                        result = await target_thread.send(content=msg)

            except Exception as e:
                logger.error(f"Some error occurred while sending thread message to {target_channel.guild.name}#{target_channel.name}: {e}")
            
            # Form message entry for every linked channel
            entry = {
                "guild_id": target_guild_id,
                "channel_id": target_channel_id,
                "thread_id": target_thread_message_id,
                "message_id": str(result.id)
            }
            message_group_entry.append(entry)
            
        else:
            logger.error(f"Target channel with ID {target_channel_id} not found")
            return
    
    # Save the message group entry to the database
    group_name = helpers.get_group_name(parent_channel_id)
    try:
        database.save_message_group_entry(group_name, message_group_entry)
        logger.info(f"Thread message successfully forwarded and saved")
    except Exception as e:
        logger.error(f"Failed to save thread message group entry: {e}")

async def handle_reply_message(bot, message: discord.Message):
    """Handles reply messages and forwards them to linked channels."""

    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Ignore messages from webhooks
    if message.webhook_id:
        return
    
    logger.info(f"Handling reply message from {message.author}")
    
    # Check if the message is in a thread and handle accordingly
    if isinstance(message.channel, discord.Thread):
        await handle_reply_message_in_thread(bot, message)
    else:
        await handle_reply_message_in_channel(bot, message)

async def handle_reply_message_in_channel(bot, message: discord.Message):
    """Handles reply messages in general channels and forwards them to linked channels."""
    
    channel_id_for_lookup = str(message.channel.id)
    target_channel_ids = helpers.find_linked_channels(channel_id_for_lookup)
    if target_channel_ids is None:
        logger.debug(f"No linked channels found for channel {channel_id_for_lookup}")
        return
    
    logger.info(f"Forwarding reply from {message.author} to {len(target_channel_ids)} linked channels")
    
    # Find the message group entry for the original message
    group_name = helpers.get_group_name(channel_id_for_lookup)
    referenced_message_id = message.reference.message_id
    referenced_message_entry = database.get_message_group_entry_by_message_id(referenced_message_id, group_name)
    
    if not referenced_message_entry:
        logger.warning(f"No message group entry found for referenced message {referenced_message_id}, treating as regular message")
        await handle_message(bot, message, from_reply=True)
        return

    # Form first message entry
    message_group_entry = [{
        "guild_id": helpers.get_guild_id_from_channel_id(str(message.channel.id)),
        "channel_id": str(message.channel.id),
        "message_id": str(message.id)
    }]

    guild_name = message.guild.name if message.guild else "Unknown Guild"
    # Form header for the message
    header = helpers.form_header(message, guild_name, len(target_channel_ids))
    msg = f"{header}\n{message.content}" if message.content else header
        
    for target_channel_id in target_channel_ids:
        target_channel = bot.get_channel(int(target_channel_id))
        target_guild_id = helpers.get_guild_id_from_channel_id(target_channel_id)
        if target_channel:
            # Get referenced message id for the target channel
            target_referenced_message_id = None
            
            for entry in referenced_message_entry:
                if entry["guild_id"] == target_guild_id and entry["channel_id"] == target_channel_id:
                    target_referenced_message_id = entry["message_id"]
                    break
                else:
                    logger.info(f"No entry found for target channel {target_channel_id} in message group entry")
                        
            try:
                reference = None
                if target_referenced_message_id:
                    reference = discord.MessageReference(message_id=int(target_referenced_message_id), channel_id=target_channel.id, guild_id=target_channel.guild.id)
            except Exception as e:
                logger.error(f"Failed to create message reference for {target_channel.guild.name}#{target_channel.name}: {e}")

            # Send the reply to the target channel
            try:
                result = await target_channel.send(
                    content=msg,
                    embed=message.embeds[0] if message.embeds else None,
                    files=[await file.to_file() for file in message.attachments],
                    reference=reference
                )
            except Exception as e:
                logger.error(f"Failed to send reply message to {target_channel.guild.name}#{target_channel.name}: {e}")
                return

            # Form message entry for every linked channel
            entry = {
                "guild_id": target_guild_id,
                "channel_id": target_channel_id,
                "message_id": str(result.id)
            }
            message_group_entry.append(entry)
        else:
            logger.error(f"Target channel with ID {target_channel_id} not found")
            return
    
    # Save the message group entry to the database
    group_name = helpers.get_group_name(channel_id_for_lookup)
    try:
        database.save_message_group_entry(group_name, message_group_entry)
        logger.info(f"Reply message successfully forwarded and saved")
    except Exception as e:
        logger.error(f"Failed to save reply message group entry: {e}")

async def handle_reply_message_in_thread(bot, message: discord.Message):
    """Handles reply messages in threads and forwards them to linked channels."""
    
    # For thread messages, use the parent channel ID
    parent_channel_id = str(message.channel.parent_id)
    target_channel_ids = helpers.find_linked_channels(parent_channel_id)
    if target_channel_ids is None:
        logger.debug(f"No linked channels found for parent channel {parent_channel_id}")
        return
    
    logger.info(f"Forwarding thread reply from {message.author} to {len(target_channel_ids)} linked channels")
    
    # Find the message group entry for the original message
    group_name = helpers.get_group_name(parent_channel_id)
    referenced_message_id = message.reference.message_id
    referenced_message_entry = database.get_message_group_entry_by_message_id(referenced_message_id, group_name)
    
    if not referenced_message_entry:
        logger.warning(f"No message group entry found for referenced message {referenced_message_id}, treating as regular message")
        await handle_message(bot, message, from_reply=True)
        return

    # Form first message entry
    message_group_entry = [{
        "guild_id": helpers.get_guild_id_from_channel_id(parent_channel_id),
        "channel_id": parent_channel_id,
        "thread_id": str(message.channel.id),
        "message_id": str(message.id)
    }]

    guild_name = message.guild.name if message.guild else "Unknown Guild"
    # Form header for the message
    header = helpers.form_header(message, guild_name, len(target_channel_ids))
    msg = f"{header}\n{message.content}" if message.content else header
        
    for target_channel_id in target_channel_ids:
        target_channel = bot.get_channel(int(target_channel_id))
        target_guild_id = helpers.get_guild_id_from_channel_id(target_channel_id)
        if target_channel:
            # Get referenced message id for the target channel
            target_referenced_message_id = None
            target_thread_id = None
            
            for entry in referenced_message_entry:
                if entry["guild_id"] == target_guild_id and entry["channel_id"] == target_channel_id:
                    target_referenced_message_id = entry["message_id"]
                    target_thread_id = entry["thread_id"]
                    break
                else:
                    logger.info(f"No entry found for target channel {target_channel_id} in thread message group entry")
            
            # Send the reply to the thread
            try:
                parent_message = await target_channel.fetch_message(target_thread_id)
            except Exception as e:
                logger.warning(f"Failed to fetch parent message in {target_channel.guild.name}#{target_channel.name}: {e}")
                return
            
            if parent_message.thread:
                target_thread = parent_message.thread
                
                # Create reference for the thread (only if referenced message is in the thread)
                reference = None
                if target_referenced_message_id:
                    try:
                        reference = discord.MessageReference(
                            message_id=int(target_referenced_message_id),
                            channel_id=target_thread.id,  # Use thread ID instead of parent channel ID
                            guild_id=target_channel.guild.id
                        )
                    except Exception as e:
                        logger.error(f"Failed to create message reference for thread {target_thread.name}: {e}")
                        reference = None
                
                # Send the reply to the thread
                result = await target_thread.send(
                    content=msg,
                    embed=message.embeds[0] if message.embeds else None,
                    files=[await file.to_file() for file in message.attachments],
                    reference=reference
                )
            else:
                logger.error(f"Parent message does not have a thread in {target_channel.guild.name}#{target_channel.name}")
                return

            # Form message entry for every linked channel
            entry = {
                "guild_id": target_guild_id,
                "channel_id": target_channel_id,
                "thread_id": target_thread_id, 
                "message_id": str(result.id)
            }
            message_group_entry.append(entry)
        else:
            logger.error(f"Target channel with ID {target_channel_id} not found")
            return
    
    # Save the message group entry to the database
    group_name = helpers.get_group_name(parent_channel_id)
    try:
        database.save_message_group_entry(group_name, message_group_entry)
        logger.info(f"Thread reply message successfully forwarded and saved")
    except Exception as e:
        logger.error(f"Failed to save reply message group entry: {e}") 