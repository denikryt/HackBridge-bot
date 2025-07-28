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
    header = helpers.form_header(message, guild_name)
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
            print(f"Target channel with ID {target_channel_id} not found.")
            return
        
    # Save the message group entry to the database
    group_name = helpers.get_group_name(str(message.channel.id))
    try:
        database.save_message_group_entry(group_name, message_group_entry)
        logger.debug(f"Message group entry saved for group {group_name}")
    except Exception as e:
        logger.error(f"Failed to save message group entry: {e}")

async def handle_reply_message(bot, message: discord.Message):
    """Handles reply messages and forwards them to linked channels."""

    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Ignore messages from webhooks
    if message.webhook_id:
        return
    
    # Try to find linked channels
    target_channel_ids = helpers.find_linked_channels(str(message.channel.id))
    if target_channel_ids is None:
        return
    
    logger.info(f"Handling reply message from {message.author} in {message.guild.name}#{message.channel.name}")
    
    # Find the message group entry for the original message
    group_name = helpers.get_group_name(str(message.channel.id))
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
    header = helpers.form_header(message, guild_name)
    msg = f"{header}\n{message.content}" if message.content else header
    
    for target_channel_id in target_channel_ids:
        target_channel = bot.get_channel(int(target_channel_id))
        target_guild_id = helpers.get_guild_id_from_channel_id(target_channel_id)
        if target_channel:
            # Get referenced message id for the target channel
            for entry in referenced_message_entry:
                if entry["guild_id"] == target_guild_id and entry["channel_id"] == target_channel_id:
                    referenced_message_id = entry["message_id"]
                    break
            # Send the reply message to the target channel
            try:
                result = await target_channel.send(
                    content=msg,
                    embed=message.embeds[0] if message.embeds else None,
                    files=[await file.to_file() for file in message.attachments],
                    reference=discord.MessageReference(message_id=referenced_message_id, channel_id=target_channel_id)
                )
                logger.debug(f"Reply message forwarded to {target_channel.guild.name}#{target_channel.name}")
            except Exception as e:
                logger.error(f"Failed to send reply message to {target_channel.guild.name}#{target_channel.name}: {e}")
                continue
            # Form message entry for every linked channel
            message_group_entry.append({
                "guild_id": target_guild_id,
                "channel_id": target_channel_id,
                "message_id": str(result.id)
            })
        else:
            logger.error(f"Target channel with ID {target_channel_id} not found")
            print(f"Target channel with ID {target_channel_id} not found.")
            return
    # Save the message group entry to the database
    group_name = helpers.get_group_name(str(message.channel.id))
    try:
        database.save_message_group_entry(group_name, message_group_entry)
        logger.debug(f"Reply message group entry saved for group {group_name}")
    except Exception as e:
        logger.error(f"Failed to save reply message group entry: {e}")