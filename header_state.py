import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

# Marker that prefixes every rendered header. Keep in sync with helpers.form_header.
HEADER_MARKER = "-# ➤"

# Time gap that breaks a block and forces a new header.
DEFAULT_IDLE_TIMEOUT = timedelta(minutes=5)


class HeaderState:
    """Manages per-destination header decisions and serialization."""

    def __init__(self, idle_timeout: timedelta = DEFAULT_IDLE_TIMEOUT):
        self.idle_timeout = idle_timeout
        self._state: Dict[str, Dict[str, object]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._group_versions: Dict[str, Dict[str, object]] = {}

    def _dest_key(self, group_name: str, channel_id: str, thread_id: Optional[str]) -> str:
        thread_part = thread_id or "root"
        return f"{group_name}:{channel_id}:{thread_part}"

    def get_lock(self, group_name: str, channel_id: str, thread_id: Optional[str]) -> asyncio.Lock:
        key = self._dest_key(group_name, channel_id, thread_id)
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    def decide_header(
        self,
        group_name: str,
        channel_id: str,
        thread_id: Optional[str],
        author_id: str,
        source_guild_id: str,
        timestamp: datetime,
        is_reply: bool = False,
    ):
        """Return (include_header, reason, prev_state)."""
        if is_reply:
            return True, "reply", self.peek_state(group_name, channel_id, thread_id)

        key = self._dest_key(group_name, channel_id, thread_id)
        prev = self._state.get(key)
        if not prev:
            return True, "no_prev_state", None

        current_version = self._group_versions.get(group_name, {}).get("version")
        if current_version is not None and prev.get("version") != current_version:
            return True, "group_source_changed", prev

        if (
            prev["author_id"] != author_id
            or prev["source_guild_id"] != source_guild_id
        ):
            return True, "author_or_source_changed", prev

        if timestamp - prev["timestamp"] > self.idle_timeout:
            return True, "idle_timeout", prev

        return False, "same_block", prev

    def should_include_header(
        self,
        group_name: str,
        channel_id: str,
        thread_id: Optional[str],
        author_id: str,
        source_guild_id: str,
        timestamp: datetime,
        is_reply: bool = False,
    ) -> bool:
        include, _, _ = self.decide_header(
            group_name=group_name,
            channel_id=channel_id,
            thread_id=thread_id,
            author_id=author_id,
            source_guild_id=source_guild_id,
            timestamp=timestamp,
            is_reply=is_reply,
        )
        return include

    def update_state(
        self,
        group_name: str,
        channel_id: str,
        thread_id: Optional[str],
        author_id: str,
        source_guild_id: str,
        timestamp: datetime,
    ):
        """Persist the latest header state after a successful send."""
        key = self._dest_key(group_name, channel_id, thread_id)
        current_version = self._group_versions.get(group_name, {}).get("version")
        self._state[key] = {
            "author_id": author_id,
            "source_guild_id": source_guild_id,
            "timestamp": timestamp,
            "version": current_version,
        }

    def peek_state(
        self,
        group_name: str,
        channel_id: str,
        thread_id: Optional[str],
    ) -> Optional[Dict[str, object]]:
        """Return the previous state for logging/inspection."""
        key = self._dest_key(group_name, channel_id, thread_id)
        return self._state.get(key)

    def update_group_source(self, group_name: str, source_guild_id: str):
        """
        Track the last source guild per group. Bump version when source changes so all destinations
        start a new block on next send.
        """
        current = self._group_versions.get(group_name)
        if not current or current.get("source_guild_id") != source_guild_id:
            new_version = (current.get("version", 0) + 1) if current else 1
            self._group_versions[group_name] = {
                "source_guild_id": source_guild_id,
                "version": new_version,
            }
            return True
        return False

    def content_has_header(self, content: str) -> bool:
        """Detect whether a mirrored message already contains a header."""
        return content.startswith(HEADER_MARKER)


header_state = HeaderState()
