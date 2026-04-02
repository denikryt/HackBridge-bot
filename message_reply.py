from datetime import timezone
import discord
import helpers
import database
import message_send
from header_state import header_state
from logger_config import get_logger

logger = get_logger(__name__)


def _is_forum_thread(thread: discord.Thread) -> bool:
    parent = thread.parent
    if parent is None:
        return False
    if isinstance(parent, discord.ForumChannel):
        return True
    return getattr(parent, "type", None) == discord.ChannelType.forum


async def handle_reply_message_in_channel(bot, message: discord.Message):
    """Handles reply messages in general channels and forwards them to linked channels."""

    timestamp = message.created_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    channel_id_for_lookup = str(message.channel.id)
    target_channel_ids = helpers.find_linked_channels(channel_id_for_lookup)
    if target_channel_ids is None:
        logger.debug(f"No linked channels found for channel {channel_id_for_lookup}")
        return

    logger.info(f"Forwarding reply from {message.author} to {len(target_channel_ids)} linked channels")

    group_name = helpers.get_group_name(channel_id_for_lookup)
    referenced_message_id = message.reference.message_id
    referenced_message_entry = database.get_message_group_entry_by_message_id(referenced_message_id, group_name)

    if not referenced_message_entry:
        logger.warning(f"No message group entry found for referenced message {referenced_message_id}, treating as regular message")
        await message_send.handle_message(bot, message)
        return

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

    for target_channel_id in target_channel_ids:
        target_channel = bot.get_channel(int(target_channel_id))
        target_guild_id = helpers.get_guild_id_from_channel_id(target_channel_id)
        if target_channel:
            target_referenced_message_id = None

            for entry in referenced_message_entry:
                if entry["guild_id"] == target_guild_id and entry["channel_id"] == target_channel_id:
                    logger.info(f"Found entry for target channel {target_channel_id} in message group entry")
                    target_referenced_message_id = entry["message_id"]
                    break
                else:
                    logger.info(f"No entry found for target channel {target_channel_id} in message group entry")

            try:
                reference = None
                if target_referenced_message_id:
                    reference = discord.MessageReference(
                        message_id=int(target_referenced_message_id),
                        channel_id=target_channel.id,
                        guild_id=target_channel.guild.id
                    )
            except Exception as e:
                logger.error(f"Failed to create message reference for {target_channel.guild.name}#{target_channel.name}: {e}")

            lock = header_state.get_lock(group_name, target_channel_id, None)
            async with lock:
                include_header, reason, prev_state = header_state.decide_header(
                    group_name=group_name,
                    channel_id=target_channel_id,
                    thread_id=None,
                    author_id=author_id,
                    source_guild_id=source_guild_id,
                    timestamp=timestamp,
                    is_reply=True,
                )

                logger.debug(
                    "[header] decision group=%s dest=%s thread=%s include=%s reason=%s author=%s source_guild=%s prev_state=%s",
                    group_name, target_channel_id, None, include_header, reason, author_id, source_guild_id, prev_state,
                )

                header = helpers.form_header(message, guild_name, channel_group_len) if include_header else ""
                msg = helpers.form_message_text(header, message.content)

                try:
                    files = await helpers.process_attachments(message)
                    global_stickers, guild_sticker_files = await helpers.process_stickers(message)
                    files += guild_sticker_files

                    result = await target_channel.send(
                        content=msg,
                        embed=message.embeds[0] if message.embeds else None,
                        files=files if files else None,
                        stickers=global_stickers if global_stickers else None,
                        reference=reference
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
                    logger.error(f"Failed to send reply message to {target_channel.guild.name}#{target_channel.name}: {e}")
                    return

                entry = {
                    "guild_id": target_guild_id,
                    "channel_id": target_channel_id,
                    "message_id": str(result.id)
                }
                message_group_entry.append(entry)
        else:
            logger.error(f"Target channel with ID {target_channel_id} not found")
            return

    group_name = helpers.get_group_name(channel_id_for_lookup)
    try:
        database.save_message_group_entry(group_name, message_group_entry)
        logger.info(f"Reply message successfully forwarded and saved")
    except Exception as e:
        logger.error(f"Failed to save reply message group entry: {e}")


async def handle_reply_message_in_thread(bot, message: discord.Message):
    """Handles reply messages in threads and forwards them to linked channels."""

    timestamp = message.created_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    logger.info(f"Handling reply message in thread from {message.author}")
    parent_channel_id = str(message.channel.parent_id)
    target_channel_ids = helpers.find_linked_channels(parent_channel_id)
    if target_channel_ids is None:
        logger.debug(f"No linked channels found for parent channel {parent_channel_id}")
        return

    logger.info(f"Forwarding thread reply from {message.author} to {len(target_channel_ids)} linked channels")

    group_name = helpers.get_group_name(parent_channel_id)
    referenced_message_id = message.reference.message_id
    referenced_message_entry = database.get_message_group_entry_by_message_id(referenced_message_id, group_name)

    if not referenced_message_entry:
        logger.warning(f"No message group entry found for referenced message {referenced_message_id}, treating as regular message")
        await message_send.handle_message(bot, message)
        return

    message_group_entry = [{
        "guild_id": helpers.get_guild_id_from_channel_id(parent_channel_id),
        "channel_id": parent_channel_id,
        "thread_id": str(message.channel.id),
        "message_id": str(message.id)
    }]

    guild_name = message.guild.name if message.guild else "Unknown Guild"
    channel_group_len = len(target_channel_ids)
    author_id = str(message.author.id)
    source_guild_id = str(message.guild.id) if message.guild else "unknown"
    source_changed = header_state.update_group_source(group_name, source_guild_id)
    if source_changed:
        logger.debug("[header] group source changed group=%s source_guild=%s", group_name, source_guild_id)

    for target_channel_id in target_channel_ids:
        target_channel = bot.get_channel(int(target_channel_id))
        target_guild_id = helpers.get_guild_id_from_channel_id(target_channel_id)
        if target_channel:
            target_referenced_message_id = None
            target_thread_id = None

            for entry in referenced_message_entry:
                if entry["guild_id"] == target_guild_id and entry["channel_id"] == target_channel_id:
                    target_referenced_message_id = entry["message_id"]
                    target_thread_id = entry["thread_id"]
                    break
                else:
                    logger.info(f"No entry found for target channel {target_channel_id} in thread message group entry")

            try:
                parent_message = await target_channel.fetch_message(target_thread_id)
            except Exception as e:
                logger.warning(f"Failed to fetch parent message in {target_channel.guild.name}#{target_channel.name}: {e}")
                return

            if parent_message.thread:
                target_thread = parent_message.thread
                reference = None
                if target_referenced_message_id:
                    try:
                        reference = discord.MessageReference(
                            message_id=int(target_referenced_message_id),
                            channel_id=target_thread.id,
                            guild_id=target_channel.guild.id
                        )
                    except Exception as e:
                        logger.error(f"Failed to create message reference for thread {target_thread.name}: {e}")
                        reference = None

                lock = header_state.get_lock(group_name, target_channel_id, target_thread.id)
                async with lock:
                    include_header, reason, prev_state = header_state.decide_header(
                        group_name=group_name,
                        channel_id=target_channel_id,
                        thread_id=str(target_thread.id),
                        author_id=author_id,
                        source_guild_id=source_guild_id,
                        timestamp=timestamp,
                        is_reply=True,
                    )

                    logger.debug(
                        "[header] decision group=%s dest=%s thread=%s include=%s reason=%s author=%s source_guild=%s prev_state=%s",
                        group_name, target_channel_id, target_thread.id, include_header, reason, author_id, source_guild_id, prev_state,
                    )

                    header = helpers.form_header(message, guild_name, channel_group_len) if include_header else ""
                    msg = helpers.form_message_text(header, message.content)

                    files = await helpers.process_attachments(message)
                    global_stickers, guild_sticker_files = await helpers.process_stickers(message)
                    files += guild_sticker_files

                    result = await target_thread.send(
                        content=msg,
                        embed=message.embeds[0] if message.embeds else None,
                        files=files if files else None,
                        stickers=global_stickers if global_stickers else None,
                        reference=reference
                    )
                    header_state.update_state(
                        group_name=group_name,
                        channel_id=target_channel_id,
                        thread_id=str(target_thread.id),
                        author_id=author_id,
                        source_guild_id=source_guild_id,
                        timestamp=timestamp,
                    )
            else:
                logger.error(f"Parent message does not have a thread in {target_channel.guild.name}#{target_channel.name}")
                return

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

    group_name = helpers.get_group_name(parent_channel_id)
    try:
        database.save_message_group_entry(group_name, message_group_entry)
        logger.info(f"Thread reply message successfully forwarded and saved")
    except Exception as e:
        logger.error(f"Failed to save reply message group entry: {e}")


async def handle_forum_thread_reply_message(bot, message: discord.Message):
    """Handles reply messages in forum threads and forwards them to linked forum threads."""
    if message.author == bot.user:
        return
    if message.webhook_id:
        return
    if not isinstance(message.channel, discord.Thread):
        return
    if not _is_forum_thread(message.channel):
        return

    parent_channel_id = str(message.channel.parent_id)
    group_name = helpers.get_group_name(parent_channel_id)
    if not group_name:
        return

    thread_entry = database.get_forum_thread_group_entry_by_thread_id(str(message.channel.id), group_name)
    if not thread_entry:
        return

    referenced_message_id = message.reference.message_id if message.reference else None
    if not referenced_message_id:
        return

    referenced_entry = database.get_message_group_entry_by_message_id(str(referenced_message_id), group_name)
    if not referenced_entry:
        await message_send.handle_forum_thread_message(bot, message, ignore_reference=True)
        return

    target_channel_ids = helpers.find_linked_channels(parent_channel_id)
    if not target_channel_ids:
        return

    timestamp = message.created_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    guild_name = message.guild.name if message.guild else "Unknown Guild"
    channel_group_len = len(target_channel_ids)
    author_id = str(message.author.id)
    source_guild_id = str(message.guild.id) if message.guild else "unknown"
    header_state.update_group_source(group_name, source_guild_id)

    message_group_entry = [{
        "guild_id": helpers.get_guild_id_from_channel_id(parent_channel_id),
        "channel_id": parent_channel_id,
        "thread_id": str(message.channel.id),
        "message_id": str(message.id)
    }]

    for entry in thread_entry:
        if entry["thread_id"] == str(message.channel.id):
            continue

        target_thread = bot.get_channel(int(entry["thread_id"]))
        if not target_thread:
            try:
                target_thread = await bot.fetch_channel(int(entry["thread_id"]))
            except Exception as e:
                logger.error(f"Failed to fetch target forum thread {entry['thread_id']}: {e}")
                continue

        target_referenced_message_id = None
        for ref_entry in referenced_entry:
            if ref_entry.get("thread_id") == entry["thread_id"]:
                target_referenced_message_id = ref_entry.get("message_id")
                break

        reference = None
        if target_referenced_message_id:
            reference = discord.MessageReference(
                message_id=int(target_referenced_message_id),
                channel_id=int(entry["thread_id"]),
                guild_id=target_thread.guild.id
            )

        lock = header_state.get_lock(group_name, entry["channel_id"], entry["thread_id"])
        async with lock:
            include_header, _, _ = header_state.decide_header(
                group_name=group_name,
                channel_id=entry["channel_id"],
                thread_id=entry["thread_id"],
                author_id=author_id,
                source_guild_id=source_guild_id,
                timestamp=timestamp,
                is_reply=True,
            )

            header = helpers.form_header(message, guild_name, channel_group_len) if include_header else ""
            msg = helpers.form_message_text(header, message.content)

            try:
                files = await helpers.process_attachments(message)
                global_stickers, guild_sticker_files = await helpers.process_stickers(message)
                files += guild_sticker_files

                result = await target_thread.send(
                    content=msg,
                    embed=message.embeds[0] if message.embeds else None,
                    files=files if files else None,
                    stickers=global_stickers if global_stickers else None,
                    reference=reference
                )
                header_state.update_state(
                    group_name=group_name,
                    channel_id=entry["channel_id"],
                    thread_id=entry["thread_id"],
                    author_id=author_id,
                    source_guild_id=source_guild_id,
                    timestamp=timestamp,
                )
                message_group_entry.append({
                    "guild_id": entry["guild_id"],
                    "channel_id": entry["channel_id"],
                    "thread_id": entry["thread_id"],
                    "message_id": str(result.id)
                })
            except Exception as e:
                logger.error(f"Failed to send forum thread reply to {entry['thread_id']}: {e}")

    try:
        database.save_message_group_entry(group_name, message_group_entry)
    except Exception as e:
        logger.error(f"Failed to save forum reply group entry: {e}")
