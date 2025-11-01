import discord
from discord.ext import commands
from config import TOKEN
import aiohttp
import io


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synchronized {len(synced)} slash commands")
    except Exception as e:
        print("Error synchronizing slash commands:", e)

# ------------------------ #


async def download_sticker_files(message: discord.Message):
    """Download static stickers from a message and return as discord.File objects."""
    files = []
    async with aiohttp.ClientSession() as session:
        for sticker in message.stickers:
            # Only handle PNG stickers
            if sticker.format == discord.StickerFormatType.png:
                async with session.get(sticker.url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        files.append(
                            discord.File(
                                io.BytesIO(data),
                                filename=f"{sticker.name}.png"
                            )
                        )
    return files

async def process_stickers(message: discord.Message):
    """Separate stickers into global (to send as stickers) and guild-native (to download as files)."""
    global_stickers = []
    guild_sticker_files = []

    if not message.stickers:
        return global_stickers, guild_sticker_files

    if message.guild:
        guild = message.guild
    else:
        guild = None

    async with aiohttp.ClientSession() as session:
        for sticker_item in message.stickers:
            print(f"--> Processing sticker: {sticker_item}")

            # Guild sticker (download as file)
            if guild and sticker_item.format == discord.StickerFormatType.png:
                try:
                    sticker = await guild.fetch_sticker(sticker_item.id)
                    if sticker.type == discord.StickerType.guild:
                        async with session.get(sticker.url) as resp:
                            if resp.status == 200:
                                data = await resp.read()
                                guild_sticker_files.append(
                                    discord.File(io.BytesIO(data), filename=f"{sticker.name}.png")
                                )
                        continue  # processed, skip sending as sticker
                except Exception as e:
                    print(f"Failed to fetch guild sticker {sticker_item.id}: {e}")
                    continue

            # Non-guild / global sticker → send as sticker
            global_stickers.append(sticker_item)

    return global_stickers, guild_sticker_files


@bot.event
async def on_message(message: discord.Message):
    # Prevent echoing the bot's own messages
    if message.author == bot.user:
        return

    # Process stickers
    global_stickers, guild_sticker_files = await process_stickers(message)

    # Only send if there's content or stickers/files
    if message.content or global_stickers or guild_sticker_files:
        await message.channel.send(
            content=message.content or None,
            stickers=global_stickers or None,
            files=guild_sticker_files or None
        )

    await bot.process_commands(message)


bot.run(TOKEN)
