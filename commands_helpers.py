
import asyncio

from roles import SuperAdmin, Admin, Registrator
import json
import logging
from typing import Any, Dict, List, Optional
import discord

logger = logging.getLogger("commands_helpers")

ROLE_CLASSES = {
    "superadmins": SuperAdmin,
    "admins": Admin,
    "registrators": Registrator
}

# ------------------------------------------
# Helper functions for roles management
# ------------------------------------------

def load_registered_channels(file_path="registered.json"):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return e

def load_roles(file_path="roles.json"):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"superadmins": [], "admins": [], "registrators": []}

def get_user_role(user_id: str, guild_id: str, roles_data: dict):
    for role_name, users in roles_data.items():
        for user in users:
            if user["user_id"] == user_id and user["guild_id"] == guild_id:
                return role_name
    return None

def has_user_permission(user_id: str, guild_id: str, permission: str) -> bool:
    roles_data = load_roles()
    role_name = get_user_role(user_id, guild_id, roles_data)

    # Check regular roles for permission
    if role_name:
        role_class = ROLE_CLASSES.get(role_name)
        if role_class and role_class().has_permission(permission):
            return True

    # Check temporary registrators separately
    for temp in roles_data.get("registrators", []):
        if temp["user_id"] == user_id and temp["guild_id"] == guild_id:
            return Registrator().has_permission(permission)

    return False

def load_linked_channels(file_path="linked_channels.json"):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return e

def remove_registrator(user_id: str, guild_id: str, file_path="roles.json"):
    with open(file_path, "r") as f:
        data = json.load(f)


    # Remove the registrator entry for the given user and guild
    data["registrators"] = [
        user for user in data.get("registrators", [])
        if not (user["user_id"] == user_id and user["guild_id"] == guild_id)
    ]

    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

#------------------------------------------
# Get functions for linked groups
#------------------------------------------

def get_group_by_name(linked_channels, group_name):
    """
    Find and return the group dict from linked_channels["groups"] with the given group_name.
    Returns the group dict if found, else None.
    """
    for group in linked_channels.get("groups", []):
        if group.get("group_name") == group_name:
            return group
    return None

def get_group_by_channel(linked_channels, guild_id, channel_id):
    """
    Returns the group dict containing the given guild_id and channel_id in its links, or None if not found.
    """
    for group in linked_channels.get("groups", []):
        for link in group.get("links", []):
            if link.get("guild_id") == guild_id and link.get("channel_id") == channel_id:
                return group
    return None

#------------------------------------------
# Various channel related checks
#------------------------------------------

async def are_all_group_channels_registered_by_user(group, registered_data, user_id):
    """
    Check if all channels in the specified group are registered by the given user_id.
    Returns (False, None) if all are registered, otherwise (True, link) for the first not registered link.
    """
    for link in group.get("links", []):
        is_registered = await is_channel_registered_by_user_id(registered_data, link["guild_id"], link["channel_id"], user_id)
        if not is_registered:
            return True, link
    return False, None

def is_channel_in_any_group(channel_id, linked_channels):
    """
    Check if the given channel_id is already part of any group in linked_channels.
    Returns True if found, False otherwise.
    """
    for group in linked_channels.get("groups", []):
        if channel_id in group.get("channel_list", []):
            return True
    return False

async def is_channel_registered_by_user(registered_channels: Dict[str, Any], interaction: discord.Interaction) -> bool:
    return any(
        entry["guild_id"] == str(interaction.guild.id) and
        entry["channel_id"] == str(interaction.channel.id) and
        entry["registrator_id"] == str(interaction.user.id)
        for entry in registered_channels["register"]
    )

async def is_channel_registered(registered_channels: Dict[str, Any], guild_id: str, channel_id: str) -> bool:
    return any(
        entry["guild_id"] == guild_id and entry["channel_id"] == channel_id
        for entry in registered_channels["register"]
    )

async def is_channel_registered_by_user_id(registered_channels: Dict[str, Any], guild_id: str, channel_id: str, user_id: str) -> bool:
    return any(
        entry["guild_id"] == guild_id and entry["channel_id"] == channel_id and entry["registrator_id"] == user_id
        for entry in registered_channels["register"]
    )

# Invite creation
async def create_invite(channel: Optional[discord.abc.GuildChannel]) -> Optional[str]:
    if channel:
        try:
            invite = await channel.create_invite(max_age=0, max_uses=0, unique=True)
            return f"https://discord.gg/{invite.code}"
        except Exception as e:
            logger.error(f"Failed to create invite for channel {getattr(channel, 'id', None)}: {e}")
    return None

# Linked group checks

def is_channel_already_linked(current_channel_id: str, target_channel_id: str, linked_channels: Dict[str, Any]) -> bool:
    for group in linked_channels["groups"]:
        if current_channel_id in group["channel_list"] and target_channel_id in group["channel_list"]:
            return True
    return False

def is_channel_in_any_group(channel_id: str, linked_channels: Dict[str, Any]) -> bool:
    for group in linked_channels["groups"]:
        if channel_id in group["channel_list"]:
            return True
    return False

def add_new_linked_group(linked_channels: Dict[str, Any], group_name: str, current_entry: Dict[str, Any], target_entry: Dict[str, Any]):
    linked_channels["groups"].append({
        "group_name": group_name,
        "channel_list": [current_entry["channel_id"], target_entry["channel_id"]],
        "links": [current_entry, target_entry]
    })

def remove_channels_from_registered(registered_channels: Dict[str, Any], channel_ids: List[str], guild_ids: List[str]):
    registered_channels["register"] = [
        entry for entry in registered_channels["register"]
        if not (
            entry["channel_id"] in channel_ids and entry["guild_id"] in guild_ids
        )
    ]

def save_json_file(filename: str, data: Any):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
