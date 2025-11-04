import discord
from discord.ext import commands
from config import TOKEN

# Intents are required for reading messages
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """
    This event works even for messages not in cache or sent before bot startup.
    """
    # Ignore bot’s own reactions
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    channel = guild.get_channel(payload.channel_id)
    if channel is None:
        return

    try:
        # Fetch the message explicitly
        message = await channel.fetch_message(payload.message_id)
        emoji = payload.emoji

        # Add the same reaction
        await message.add_reaction(emoji)
        print(f"Echoed {emoji} on message {message.id}")

    except discord.Forbidden:
        print("Missing permissions to add reactions.")
    except discord.NotFound:
        print("Message not found (may have been deleted).")
    except discord.HTTPException as e:
        print(f"Failed to add reaction: {e}")

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """Remove the bot's reaction when the user removes theirs."""
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel:
        return

    try:
        message = await channel.fetch_message(payload.message_id)
        emoji = payload.emoji

        # Try to find the bot's own reaction to remove
        for reaction in message.reactions:
            if str(reaction.emoji) == str(emoji):
                async for user in reaction.users():
                    if user.id == bot.user.id:
                        await message.remove_reaction(emoji, bot.user)
                        print(f"➖ Removed echo reaction {emoji} from message {message.id}")
                        return
    except discord.Forbidden:
        print("❌ Missing permissions to remove reactions.")
    except discord.NotFound:
        print("⚠️ Message not found (maybe deleted).")
    except discord.HTTPException as e:
        print(f"Error removing reaction: {e}")

bot.run(TOKEN)
