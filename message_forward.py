from datetime import timezone
import discord
import emoji
import helpers
import database
from header_state import header_state
from logger_config import get_logger
import json

logger = get_logger(__name__)

async def handle_forward_message(bot, message: discord.Message):
    """Handles forward messages and forwards them to all linked channels."""

    timestamp = message.created_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    forwarded_text = ""
    forwarded_attachments = []
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
    channel_group_len = len(target_channel_ids)
    author_id = str(message.author.id)
    source_guild_id = str(message.guild.id) if message.guild else "unknown"
    source_changed = header_state.update_group_source(group_name, source_guild_id)
    if source_changed:
        logger.debug("[header] group source changed group=%s source_guild=%s", group_name, source_guild_id)
    
    forwarded_label = f"_Forwarded message_ {emoji.emojize(':arrow_heading_down:')}"
    body = f"{forwarded_label}\n{forwarded_text}" if forwarded_text else forwarded_label
        
    for target_channel_id in target_channel_ids:
        target_channel = bot.get_channel(int(target_channel_id))
        target_guild_id = helpers.get_guild_id_from_channel_id(target_channel_id)
        if target_channel:
            lock = header_state.get_lock(group_name, target_channel_id, None)
            async with lock:
                include_header, reason, prev_state = header_state.decide_header(
                    group_name=group_name,
                    channel_id=target_channel_id,
                    thread_id=None,
                    author_id=author_id,
                    source_guild_id=source_guild_id,
                    timestamp=timestamp,
                    is_reply=False,
                )

                logger.debug(
                    "[header] decision group=%s dest=%s thread=%s include=%s reason=%s author=%s source_guild=%s prev_state=%s",
                    group_name, target_channel_id, None, include_header, reason, author_id, source_guild_id, prev_state,
                )

                header = helpers.form_header(message, guild_name, channel_group_len) if include_header else ""
                msg = helpers.form_message_text(header, body)

                # Send the forwarded message to the target channel
                try:
                    result = await target_channel.send(
                        content=msg,
                        embed=message.embeds[0] if message.embeds else None,
                        files=[await file.to_file() for file in forwarded_attachments] if forwarded_attachments else None
                    )
                    header_state.update_state(
                        group_name=group_name,
                        channel_id=target_channel_id,
                        thread_id=None,
                        author_id=author_id,
                        source_guild_id=source_guild_id,
                        timestamp=timestamp,
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
