import discord
import helpers
import database
from logger_config import get_logger

logger = get_logger(__name__)


async def handle_reaction_add(bot, payload: discord.RawReactionActionEvent):
    """Propagate reaction additions to all linked messages."""
    await _process_reaction(bot, payload, operation="add")


async def handle_reaction_remove(bot, payload: discord.RawReactionActionEvent):
    """Propagate reaction removals to all linked messages."""
    await _process_reaction(bot, payload, operation="remove")


async def _process_reaction(bot, payload: discord.RawReactionActionEvent, operation: str):
    """Route reaction events between regular channels and threads."""
    if payload.user_id == bot.user.id:
        return

    if not payload.guild_id:
        logger.debug("Reaction event without guild_id; ignoring.")
        return

    channel = await _resolve_channel(bot, payload.guild_id, payload.channel_id)
    if channel is None:
        logger.warning(f"Unable to resolve channel {payload.channel_id} for reaction event.")
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.Forbidden:
        logger.error(f"No permission to fetch message {payload.message_id} in channel {channel.id}")
        return
    except discord.NotFound:
        logger.warning(f"Message {payload.message_id} not found in channel {channel.id}")
        return
    except discord.HTTPException as exc:
        logger.error(f"Failed to fetch message {payload.message_id}: {exc}")
        return

    emoji = payload.emoji

    if isinstance(channel, discord.Thread):
        await _process_thread_message_reaction(bot, message, emoji, operation)
    else:
        await _process_channel_message_reaction(bot, message, emoji, operation)


async def _process_channel_message_reaction(bot, message: discord.Message, emoji, operation: str):
    """Handle reaction propagation for messages in regular channels."""
    channel_id = str(message.channel.id)
    target_channel_ids = helpers.find_linked_channels(channel_id)
    if target_channel_ids is None:
        logger.debug(f"No linked channels configured for channel {channel_id}")
        return

    group_name = helpers.get_group_name(channel_id)
    if not group_name:
        logger.warning(f"No group name found for channel {channel_id}")
        return

    message_entry = database.get_message_group_entry_by_message_id(str(message.id), group_name)
    if not message_entry:
        logger.debug(f"No message entry found for message {message.id} in group {group_name}")
        return

    source_guild_id = helpers.get_guild_id_from_channel_id(channel_id)

    for entry in message_entry:
        if entry["channel_id"] == channel_id and entry["guild_id"] == source_guild_id:
            continue

        await _apply_reaction_to_entry(bot, entry, emoji, operation)


async def _process_thread_message_reaction(bot, message: discord.Message, emoji, operation: str):
    """Handle reaction propagation for messages posted inside threads."""
    thread = message.channel
    parent_channel_id = str(thread.parent_id)
    target_channel_ids = helpers.find_linked_channels(parent_channel_id)
    if target_channel_ids is None:
        logger.debug(f"No linked channels configured for parent channel {parent_channel_id}")
        return

    group_name = helpers.get_group_name(parent_channel_id)
    if not group_name:
        logger.warning(f"No group name found for parent channel {parent_channel_id}")
        return

    message_entry = database.get_message_group_entry_by_message_id(str(message.id), group_name)
    if not message_entry:
        logger.debug(f"No thread message entry found for message {message.id} in group {group_name}")
        return

    source_guild_id = helpers.get_guild_id_from_channel_id(parent_channel_id)
    thread_id = str(thread.id)

    for entry in message_entry:
        if (
            entry["channel_id"] == parent_channel_id
            and entry["guild_id"] == source_guild_id
            and entry.get("thread_id") == thread_id
        ):
            continue

        await _apply_reaction_to_entry(bot, entry, emoji, operation)


async def _apply_reaction_to_entry(bot, entry: dict, emoji, operation: str):
    """Fetch the linked message represented by entry and apply the requested reaction operation."""
    target_channel = await _resolve_channel(bot, entry.get("guild_id"), entry["channel_id"])
    if target_channel is None:
        logger.warning(f"Target channel {entry['channel_id']} could not be resolved for reaction sync.")
        return

    try:
        if "thread_id" in entry:
            parent_message = await target_channel.fetch_message(int(entry["thread_id"]))
            target_thread = parent_message.thread
            if not target_thread:
                logger.warning(f"No thread found for parent message {entry['thread_id']} in channel {target_channel.id}")
                return
            target_message = await target_thread.fetch_message(int(entry["message_id"]))
        else:
            target_message = await target_channel.fetch_message(int(entry["message_id"]))
    except discord.Forbidden:
        logger.error(f"No permission to fetch linked message {entry['message_id']} in channel {target_channel.id}")
        return
    except discord.NotFound:
        logger.warning(f"Linked message {entry['message_id']} not found in channel {target_channel.id}")
        return
    except discord.HTTPException as exc:
        logger.error(f"Failed to fetch linked message {entry['message_id']}: {exc}")
        return

    await _apply_reaction(bot, target_message, emoji, operation)


async def _apply_reaction(bot, message: discord.Message, emoji, operation: str):
    """Add or remove the specified reaction on the provided message."""
    try:
        if operation == "add":
            await message.add_reaction(emoji)
        elif operation == "remove":
            await message.remove_reaction(emoji, bot.user)
    except discord.HTTPException as exc:
        if operation == "add" and exc.status == 400:
            logger.debug(f"Reaction {emoji} already exists on message {message.id}")
        elif operation == "remove" and exc.status == 404:
            logger.debug(f"Reaction {emoji} from bot not present on message {message.id}")
        else:
            logger.error(f"Failed to {operation} reaction {emoji} on message {message.id}: {exc}")


async def _resolve_channel(bot, guild_id, channel_id):
    """Resolve a channel by ID using cache first, then API fetch as fallback."""
    channel = bot.get_channel(int(channel_id))
    if channel:
        return channel

    guild = bot.get_guild(int(guild_id)) if guild_id else None
    if guild:
        channel = guild.get_channel(int(channel_id))
        if channel:
            return channel

    try:
        return await bot.fetch_channel(int(channel_id))
    except (discord.NotFound, discord.Forbidden):
        return None
    except discord.HTTPException:
        logger.error(f"HTTP error while fetching channel {channel_id}")
        return None
