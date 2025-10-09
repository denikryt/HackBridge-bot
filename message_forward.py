import discord
import emoji
import helpers
import database
from logger_config import get_logger
import json

logger = get_logger(__name__)

async def handle_forward_message(bot, message: discord.Message):
    """Handles forward messages and forwards them to all linked channels."""

    snapshots = getattr(message, "message_snapshots", [])
    for snap in snapshots:
        forwarded_text = getattr(snap, "content", "")
        forwarded_text = f"> {forwarded_text.replace('\n', '\n> ')}" if forwarded_text else ""
        forwarded_attachments = getattr(snap, "attachments", [])

    channel_id_for_lookup = str(message.channel.id)
    target_channel_ids = helpers.find_linked_channels(channel_id_for_lookup)
    if target_channel_ids is None:
        logger.debug(f"No linked channels found for channel {channel_id_for_lookup}")
        return

    # Find the message group entry for the original message
    group_name = helpers.get_group_name(channel_id_for_lookup)

    # Form first message entry
    message_group_entry = [{
        "guild_id": helpers.get_guild_id_from_channel_id(str(message.channel.id)),
        "channel_id": str(message.channel.id),
        "message_id": str(message.id)
    }]

    guild_name = message.guild.name if message.guild else "Unknown Guild"
    
    # Form header for the message
    header = helpers.form_header(message, guild_name, len(target_channel_ids))
    msg = f"{header}_Forwarded message_ {emoji.emojize(':arrow_heading_down:')}\n{forwarded_text}" if forwarded_text else header
        
    for target_channel_id in target_channel_ids:
        target_channel = bot.get_channel(int(target_channel_id))
        target_guild_id = helpers.get_guild_id_from_channel_id(target_channel_id)
        if target_channel:
            # Send the forwarded message to the target channel
            try:
                result = await target_channel.send(
                    content=msg,
                    embed=message.embeds[0] if message.embeds else None,
                    files=[await file.to_file() for file in forwarded_attachments]
                )
            except Exception as e:
                logger.error(f"Failed to send forwarded message to {target_channel.guild.name}#{target_channel.name}: {e}")
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
        logger.info(f"Forwarded message successfully sent and saved")
    except Exception as e:
        logger.error(f"Failed to save forwarded message group entry: {e}")
