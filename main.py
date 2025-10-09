from discord.ext import commands
from discord import app_commands
import discord
import json
import logging
from config import TOKEN
import commands as command_module
import message_edit
import message_delete
from message_worker import MessageWorker
from logger_config import setup_logging, get_logger

# Setup logging before anything else
setup_logging()
logger = get_logger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
message_worker = MessageWorker(bot)

# Create files if they do not exist
def create_files():
    try:
        with open("roles.json", "x") as f:
            json.dump({"superadmins": [], "admins": [], "temporary_registrators": []}, f, indent=2)
    except FileExistsError:
        pass

    try:
        with open("registered.json", "x") as f:
            json.dump({"register": []}, f, indent=2)
    except FileExistsError:
        pass

    try:
        with open("linked_channels.json", "x") as f:
            json.dump({"groups": []}, f, indent=2)
    except FileExistsError:
        pass

create_files()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synchronized {len(synced)} slash commands")
    except Exception as e:
        logger.error(f"Error syncing slash commands: {e}")
        print("Error synchronizing slash commands:", e)

@bot.event
async def on_message(message):
    await message_worker.process_message(message)
    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    await message_edit.handle_message_edit(bot, before, after)

@bot.event
async def on_message_delete(message):
    await message_delete.handle_message_delete(bot, message)

@bot.event
async def on_command_error(ctx, error):
    logger.error(f"Command error in {ctx.command}: {error}")
    if isinstance(error, commands.CommandNotFound):
        logger.debug(f"Command not found: {ctx.message.content}")
    elif isinstance(error, commands.MissingPermissions):
        logger.warning(f"Missing permissions for {ctx.author} in {ctx.guild}: {error}")
    else:
        logger.error(f"Unexpected command error: {error}")

# Register commands
command_module.setup(bot)

bot.run(TOKEN)