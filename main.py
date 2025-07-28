from discord.ext import commands
from discord import app_commands
import discord
import json
import logging
from config import TOKEN
import commands as command_module
import messages as message_module
from logger_config import setup_logging, get_logger

# Setup logging before anything else
setup_logging()
logger = get_logger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

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
    try:
        await message_module.handle_message(bot, message)
        await bot.process_commands(message)
    except Exception as e:
        logger.error(f"Error handling message from {message.author} in {message.guild}: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"Unhandled error in event {event}: {args}, {kwargs}")

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
# ------------------------------------------
# + если делаешь линк на тот же канал откуда пишешь
# + удалять записи из registered.json когда делаешь линк
#   + не удаляется interation.guild.id и interaction.channel.id 
# + когда удаляешь линк, удалять целую группу из links.json если остается один канал
# + правильное отображение имен каналов и серверов в links.json
# + написать команду remove_admin, remove_registrator
# + autocomplete для команд remove_admin, remove_registrator
# + имя админа в команде show_admins не отображается
# + в roles.json поменять id на user_id и в командах какие используют roles.json тоже поменять
# + создать файлы roles.json, registered.json, links.json если их нет
# + сделать проверку, если юзер суперадмин, то он не может быть админом, если админ, то не может быть временным регистратором
# чтобы команда show_admins показывала и суперадминов и админов
# + эмоджи в имени админа отображаются некорректно
# + чтобы можно было объединять в группы три и более каналов
# подебажить команду link_channel_to_group
    # - добавляет канал из этой же группы
    # - если какой-то канал из группы не зарегистрирован
    # - если вызывать команду link_channel в канале, который не связан с группой, на канал который уже связан с группой - ломается
    # + если канал из группы не зарегистрирован ломается autocomplete
# + в links.json группы должны быть с именем группы, а не просто links
# + по команде link_channel чтобы autocomplete показывало только каналы, которые зарегистрировал определенный регистратор
# + и чтобы объединять каналы можно было только те, которые закреплены за этим регистратором
# + autocomplete по юзерам на сервере для команд set_admin, set_registrator
# - сделать отдельный список айди каналов в registered.json, чтобы было проще проверять, зарегистрирован ли канал
# + давать названия группам каналов
# + отедельная команда для добавления канала в уже существующую группу
# + чтобы команда show_registered_channels показывала только каналы, зарегистрированные этим регистратором
# + сейчас можно удалить зарегистрированный канал от другого регистратратора и оно скажет "This channel is not registered for message forwarding."
# + команде show_linked_channels показывать название группы, к которой принадлежит канал и вообще все каналы в этой группе
# + чтобы суперадмином мог быть только один на сервере
# + команда remove_channel_registration при вызове удаляет регистрацию, но говорит, что канал не зарегистрирован
# + чтобы если канал уже зарегистрирован одним регистратором, то другой регистратор не мог его зарегистрировать, только админ или суперадмин может удалить регистрацию
# ? чтобы команда show_registered_channels показывала только каналы от этого регистратратора, а для админа и суперадмина дополнительно все каналы на сервере
# ? отдельные команды show_my_registered_channels и show_guild_registered_channels
# чтобы команда show_registered_channels показывала регистраторов каналов