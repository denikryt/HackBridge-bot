import time
from datetime import timezone
import discord
import helpers
import database
from header_state import header_state
from logger_config import get_logger

logger = get_logger(__name__)

IGNORE_TTL_SECONDS = 10.0


class ForumSync:
    def __init__(self, bot):
        self.bot = bot
        self._ignore_until = {}

    def register_listeners(self):
        self.bot.add_listener(self.on_thread_create)
        self.bot.add_listener(self.on_thread_update)
        self.bot.add_listener(self.on_thread_delete)

    def is_forum_thread(self, thread: discord.Thread) -> bool:
        parent = thread.parent
        if parent is None:
            return False
        if isinstance(parent, discord.ForumChannel):
            return True
        return getattr(parent, "type", None) == discord.ChannelType.forum

    def _mark_ignore(self, thread_id: str):
        self._ignore_until[str(thread_id)] = time.monotonic() + IGNORE_TTL_SECONDS

    def _should_ignore(self, thread_id: str) -> bool:
        if not thread_id:
            return False
        thread_id = str(thread_id)
        expiry = self._ignore_until.get(thread_id)
        if expiry is None:
            return False
        if time.monotonic() >= expiry:
            self._ignore_until.pop(thread_id, None)
            return False
        return True

    async def on_thread_create(self, thread: discord.Thread):
        if not self.is_forum_thread(thread):
            return
        if self._should_ignore(thread.id):
            return
        if getattr(thread, "owner_id", None) == self.bot.user.id:
            return

        parent_channel_id = str(thread.parent_id)
        target_channel_ids = helpers.find_linked_channels(parent_channel_id)
        if not target_channel_ids:
            return

        group_name = helpers.get_group_name(parent_channel_id)
        if not group_name:
            return

        starter_message = await self._fetch_starter_message(thread)
        if not starter_message:
            logger.warning("Unable to fetch starter message for forum thread %s", thread.id)
            return

        thread_group_entry = [{
            "guild_id": helpers.get_guild_id_from_channel_id(parent_channel_id),
            "channel_id": parent_channel_id,
            "thread_id": str(thread.id),
            "starter_message_id": str(starter_message.id)
        }]

        source_guild_id = str(starter_message.guild.id) if starter_message.guild else "unknown"
        header_state.update_group_source(group_name, source_guild_id)

        for target_channel_id in target_channel_ids:
            target_forum = await self._resolve_forum_channel(target_channel_id)
            if not target_forum:
                logger.warning("Target forum channel %s not found", target_channel_id)
                continue
            if not isinstance(target_forum, discord.ForumChannel) and getattr(target_forum, "type", None) != discord.ChannelType.forum:
                logger.warning("Target channel %s is not a forum channel", target_channel_id)
                continue

            try:
                files, stickers = await self._build_files_and_stickers(starter_message)
                content = starter_message.content or ""
                header = helpers.form_header(starter_message, starter_message.guild.name if starter_message.guild else "Unknown Guild", len(target_channel_ids))
                body = helpers.form_message_text(header, content)
                embeds = starter_message.embeds if starter_message.embeds else None
                applied_tags = self._map_tags_by_name(thread.applied_tags, target_forum)

                result = await target_forum.create_thread(
                    name=thread.name,
                    content=body if body else None,
                    files=files or [],
                    embeds=embeds or [],
                    stickers=stickers or [],
                    applied_tags=applied_tags or []
                )
                target_thread = getattr(result, "thread", result)
                target_message = getattr(result, "message", None)
                starter_message_id = str(target_message.id) if target_message else None
                if not starter_message_id:
                    fetched = await self._fetch_starter_message(target_thread)
                    starter_message_id = str(fetched.id) if fetched else None

                self._mark_ignore(target_thread.id)
                header_state.update_state(
                    group_name=group_name,
                    channel_id=target_channel_id,
                    thread_id=str(target_thread.id),
                    author_id=str(starter_message.author.id),
                    source_guild_id=source_guild_id,
                    timestamp=starter_message.created_at,
                )
                thread_group_entry.append({
                    "guild_id": helpers.get_guild_id_from_channel_id(target_channel_id),
                    "channel_id": target_channel_id,
                    "thread_id": str(target_thread.id),
                    "starter_message_id": starter_message_id
                })
            except Exception as exc:
                logger.error("Failed to create synced forum thread in %s: %s", target_channel_id, exc)

        if len(thread_group_entry) > 1:
            try:
                database.save_forum_thread_group_entry(group_name, thread_group_entry)
                logger.info("Saved forum thread mapping for thread %s", thread.id)
            except Exception as exc:
                logger.error("Failed to save forum thread mapping: %s", exc)
            starter_message_entry = [
                {
                    "guild_id": entry["guild_id"],
                    "channel_id": entry["channel_id"],
                    "thread_id": entry["thread_id"],
                    "message_id": entry.get("starter_message_id"),
                }
                for entry in thread_group_entry
                if entry.get("starter_message_id")
            ]
            if starter_message_entry:
                try:
                    database.save_message_group_entry(group_name, starter_message_entry)
                except Exception as exc:
                    logger.error("Failed to save forum starter message mapping: %s", exc)

    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        if not self.is_forum_thread(after):
            return
        if self._should_ignore(after.id):
            return

        before_tags = self._tag_names(before.applied_tags)
        after_tags = self._tag_names(after.applied_tags)
        name_changed = before.name != after.name
        tags_changed = before_tags != after_tags
        if not name_changed and not tags_changed:
            return

        parent_channel_id = str(after.parent_id)
        group_name = helpers.get_group_name(parent_channel_id)
        if not group_name:
            return

        thread_entry = database.get_forum_thread_group_entry_by_thread_id(str(after.id), group_name)
        if not thread_entry:
            return

        for entry in thread_entry:
            if entry["thread_id"] == str(after.id):
                continue

            target_thread = await self._resolve_thread(entry["thread_id"])
            if not target_thread:
                continue

            kwargs = {}
            if name_changed:
                kwargs["name"] = after.name

            if tags_changed:
                target_forum = await self._resolve_forum_channel(entry["channel_id"])
                if target_forum:
                    mapped_tags = self._map_tags_by_name(after.applied_tags, target_forum)
                    kwargs["applied_tags"] = mapped_tags if mapped_tags else []

            if not kwargs:
                continue

            try:
                self._mark_ignore(target_thread.id)
                await target_thread.edit(**kwargs)
            except Exception as exc:
                logger.error("Failed to update forum thread %s: %s", entry["thread_id"], exc)

    async def on_thread_delete(self, thread: discord.Thread):
        if not self.is_forum_thread(thread):
            return
        if self._should_ignore(thread.id):
            return

        parent_channel_id = str(thread.parent_id)
        group_name = helpers.get_group_name(parent_channel_id)
        if not group_name:
            return

        thread_entry = database.get_forum_thread_group_entry_by_thread_id(str(thread.id), group_name)
        if not thread_entry:
            return

        for entry in thread_entry:
            if entry["thread_id"] == str(thread.id):
                continue
            target_thread = await self._resolve_thread(entry["thread_id"])
            if not target_thread:
                continue
            try:
                self._mark_ignore(target_thread.id)
                await target_thread.delete()
            except Exception as exc:
                logger.error("Failed to delete synced forum thread %s: %s", entry["thread_id"], exc)

        try:
            database.delete_forum_thread_group_entry_by_thread_id(str(thread.id), group_name)
        except Exception as exc:
            logger.error("Failed to remove forum thread mapping for %s: %s", thread.id, exc)

    async def _fetch_starter_message(self, thread: discord.Thread):
        try:
            return await thread.fetch_message(thread.id)
        except Exception:
            try:
                async for msg in thread.history(limit=1, oldest_first=True):
                    return msg
            except Exception:
                return None

    async def _resolve_forum_channel(self, channel_id: str):
        channel = self.bot.get_channel(int(channel_id))
        if channel:
            return channel
        try:
            return await self.bot.fetch_channel(int(channel_id))
        except Exception:
            return None

    async def _resolve_thread(self, thread_id: str):
        channel = self.bot.get_channel(int(thread_id))
        if channel:
            return channel
        try:
            return await self.bot.fetch_channel(int(thread_id))
        except Exception:
            return None

    async def _build_files_and_stickers(self, message: discord.Message):
        files = await helpers.process_attachments(message)
        global_stickers, guild_sticker_files = await helpers.process_stickers(message)
        files += guild_sticker_files
        return files, global_stickers

    def _map_tags_by_name(self, source_tags, target_forum):
        if not source_tags or not target_forum:
            return []
        available_tags = getattr(target_forum, "available_tags", None)
        if not available_tags:
            return []
        source_names = {tag.name for tag in source_tags}
        return [tag for tag in available_tags if tag.name in source_names]

    def _tag_names(self, tags):
        return {tag.name for tag in tags} if tags else set()


def setup(bot):
    sync = ForumSync(bot)
    sync.register_listeners()
    return sync
