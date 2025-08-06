from roles import SuperAdmin, Admin, Registrator
import json 
import config
import emoji
import discord
import random

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
    except FileNotFoundError:
        return {"register": []}
    
def load_roles(file_path="roles.json"):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"superadmins": [], "admins": [], "registrators": []}
    
def load_linked_channels(file_path="linked_channels.json"):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"groups": []} 

def get_user_role(user_id: str, guild_id: str, roles_data: dict):
    for role_name, users in roles_data.items():
        for user in users:
            if user["user_id"] == user_id and user["guild_id"] == guild_id:
                return role_name
    return None

def has_user_permission(user_id: str, guild_id: str, permission: str) -> bool:
    roles_data = load_roles()
    role_name = get_user_role(user_id, guild_id, roles_data)

    # Проверка обычных ролей
    if role_name:
        role_class = ROLE_CLASSES.get(role_name)
        if role_class and role_class().has_permission(permission):
            return True

    # Проверка временных регистраторов отдельно
    for temp in roles_data.get("registrators", []):
        if temp["user_id"] == user_id and temp["guild_id"] == guild_id:
            return Registrator().has_permission(permission)

    return False

def remove_registrator(user_id: str, guild_id: str, file_path="roles.json"):
    with open(file_path, "r") as f:
        data = json.load(f)

    data["registrators"] = [
        user for user in data.get("registrators", [])
        if not (user["user_id"] == user_id and user["guild_id"] == guild_id)
    ]

    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

# ------------------------------------------
# Helper functions for message handling
# ------------------------------------------

def find_linked_channels(channel_id: str, file_path="linked_channels.json"):
    linked_channels = load_linked_channels(file_path)
    for group in linked_channels["groups"]:
        # Check if the channel_id is in the group's channels
        if channel_id in group["channel_list"]:
            group["channel_list"].remove(channel_id)
            return group["channel_list"]

    return None

def get_group_name(channel_id: str, file_path="linked_channels.json"):
    linked_channels = load_linked_channels(file_path)
    for group in linked_channels["groups"]:
        if channel_id in group["channel_list"]:
            return group["group_name"]
    return None

def get_guild_id_from_channel_id(channel_id: str, file_path="linked_channels.json"):
    linked_channels = load_linked_channels(file_path)
    for group in linked_channels["groups"]:
        if channel_id in group["channel_list"]:
            for entry in group["links"]:
                if entry["channel_id"] == channel_id:
                    return entry["guild_id"]
    return None

async def get_or_create_webhook(target_channel):
    webhooks = await target_channel.webhooks()
    webhook = next((wh for wh in webhooks if wh.name == config.WEBHOOK_NAME), None)
    if not webhook:
        # Create a new webhook with avatar if it doesn't exist 
        with open(config.AVATAR_PATH, "rb") as avatar_file:
            avatar_data = avatar_file.read()
            webhook = await target_channel.create_webhook(
                name=config.WEBHOOK_NAME,
                avatar=avatar_data
            )
        
        print(f"Created webhook in {target_channel.name} with ID {webhook.id}")
    return webhook

def form_header(message: discord.Message, guild_name: str, channel_group_len: int) -> str:
    user_name = message.author.display_name
    # Remove emojis from user name
    user_name = emoji.demojize(user_name)
    # Remove emoji codes (pattern :emoji_name:)
    import re
    user_name = re.sub(r':[a-zA-Z0-9_+-]+:', '', user_name)
    user_name = user_name.strip()  # Remove any extra whitespace
    
    user_id = message.author.id
    guild_id = message.guild.id

    # Get user's custom avatar emoji or use random default
    import database
    user_avatar = database.get_user_avatar(str(user_id))
    if user_avatar:
        avatar_emoji = user_avatar
    else:
        # Use random emoji from config if no custom avatar is set
        avatar_emoji = emoji.emojize(config.DEFAULT_AVATAR)

    # Ссылка на профиль (оборачиваем в < > — чтобы не было preview)
    user_link = f"<https://discord.com/users/{user_id}>"
    nickname = f"{avatar_emoji} **[{user_name}]({user_link})**"

    # Ссылка на сервер (тоже без preview)
    guild_link = f"<https://discord.com/channels/{guild_id}>"
    guild_name_formatted = f"{emoji.emojize(':loud_sound:')} _**[{guild_name}]({guild_link})**_"

    header = f"{nickname} {guild_name_formatted}"

    return header

def validate_single_emoji(emoji_string: str) -> bool:
    """
    Validate that the input is a single emoji (Unicode or Discord custom emoji).
    
    Args:
        emoji_string: The string to validate
        
    Returns:
        bool: True if the string contains exactly one valid emoji, False otherwise
    """
    import re
    
    emoji_string = emoji_string.strip()
    if not emoji_string:
        return False

    # Check if there are more than 2 ":" symbols - if so, return False
    colon_count = emoji_string.count(":")
    if colon_count > 2:
        return False

    # Regex for Discord custom emoji: <:name:id> or <a:name:id>
    discord_emoji_pattern = re.compile(r"^<a?:\w+:\d+>$")
    
    # If it's a Discord custom emoji, it's valid
    if discord_emoji_pattern.match(emoji_string):
        return True

    # For Unicode emoji, use the emoji library if available
    try:
        import emoji as emoji_lib
        # Check if it's a single Unicode emoji
        emoji_count = len(emoji_lib.emoji_list(emoji_string))
        return emoji_count == 1
    except ImportError:
        # Fallback: simple check for common Unicode emoji ranges
        unicode_emoji_pattern = re.compile(
            r"^(?:[\U0001F1E6-\U0001F1FF]{2}|[\U0001F600-\U0001F64F]|[\U0001F300-\U0001F5FF]|[\U0001F680-\U0001F6FF]|[\U0001F700-\U0001F77F]|[\U0001F780-\U0001F7FF]|[\U0001F800-\U0001F8FF]|[\U0001F900-\U0001F9FF]|[\U0001FA00-\U0001FA6F]|[\U0001FA70-\U0001FAFF]|[\U00002702-\U000027B0]|[\U000024C2-\U0001F251])$"
        )
        return bool(unicode_emoji_pattern.match(emoji_string))
