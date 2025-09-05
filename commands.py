from discord import app_commands
from discord.ext import commands
import discord
import json
from roles import SuperAdmin, Admin, Registrator
import helpers
from logger_config import get_logger
import database
import commands_helpers

# Set up logger for commands module
logger = get_logger(__name__)


def setup(bot):
    @bot.tree.command(name="update_invites", description="Regenerate and update invite links for all linked channels in a group")
    async def update_invites(interaction: discord.Interaction):
        '''Regenerate and update invite links for every linked channel in a group, regardless of existing data.'''
        logger.info(f"update_invites command invoked by {interaction.user.display_name} ({interaction.user.id})")

        try:
            linked_channels = commands_helpers.load_linked_channels()
        except Exception as e:
            logger.error(f"Failed to load linked channels: {e}")
            await interaction.response.send_message("An error occurred while loading linked channels data.", ephemeral=True)
            return

        # Find the group containing the current channel using helper
        group = commands_helpers.get_group_by_channel(linked_channels, str(interaction.guild.id), str(interaction.channel.id))

        if not group:
            await interaction.response.send_message("This channel is not part of any linked channels group.", ephemeral=True)
            return

        updated = False
        msg = f"Invite links for group **{group.get('group_name')}** regenerated and updated:\n"
        failed_guilds = []
        for link in group.get("links", []):
            channel_id = link.get("channel_id")
            guild_id = link.get("guild_id")
            channel_obj = None
            guild_obj = bot.get_guild(int(guild_id)) if guild_id else None
            if guild_obj:
                channel_obj = guild_obj.get_channel(int(channel_id)) if channel_id else None
            if channel_obj:
                new_invite = await commands_helpers.create_invite(channel_obj)
                if new_invite:
                    # Always update or create the invite_url entry
                    link["invite_url"] = new_invite
                    updated = True
                    msg += f"→ [{link.get('guild_name')}]({new_invite}) | #**{link.get('channel_name')}** (updated)\n"
                else:
                    msg += f"→ [{link.get('guild_name')}] | #**{link.get('channel_name')}** (failed to create)\n"
                    failed_guilds.append(link.get('guild_name'))
            else:
                # If channel not found, but invite_url doesn't exist, do not create
                msg += f"→ [{link.get('guild_name')}] | #**{link.get('channel_name')}** (channel not found)\n"
                failed_guilds.append(link.get('guild_name'))

        # Send additional ephemeral message for guilds where invite link was not created
        if failed_guilds:
            await interaction.followup.send(
                f"Invite link was not created for the following guilds: {', '.join(set(failed_guilds))}",
                ephemeral=True
            )

        if updated:
            try:
                commands_helpers.save_json_file("linked_channels.json", linked_channels)
                logger.info(f"Updated invite links for group {group.get('group_name')}")
            except Exception as e:
                logger.error(f"Failed to save linked channels data: {e}")
                await interaction.response.send_message("An error occurred while saving updated invite links.", ephemeral=True)
                return

        await interaction.response.send_message(msg, ephemeral=True)
    # ------------------------------------------
    # Functions for autocompletion
    # ------------------------------------------

    async def autocomplete_guild_id(interaction: discord.Interaction, current: str):
        logger.debug(f"autocomplete_guild_id called by {interaction.user.display_name} ({interaction.user.id}) with query: '{current}'")
        try:
            with open("registered.json", "r") as f:
                data = json.load(f)
            logger.debug("Successfully loaded registered.json for autocomplete")
        except FileNotFoundError:
            logger.warning("registered.json not found for autocomplete")
            return []
        except Exception as e:
            logger.error(f"Error loading registered.json for autocomplete: {e}")
            return []
        
        # Get all guild IDs where the user is a registrator
        guild_ids = list({entry["guild_id"] for entry in data["register"] if entry['registrator_id'] == str(interaction.user.id)})
        if str(interaction.guild.id) in guild_ids:
            guild_ids.remove(str(interaction.guild.id)) 

        guild_names = {
            gid: bot.get_guild(int(gid)).name if bot.get_guild(int(gid)) else f"Guild {gid}"
            for gid in guild_ids
        }

        results = [
            app_commands.Choice(name=f"{guild_names[gid]} ({gid})", value=gid)
            for gid in guild_ids if current.lower() in gid or current.lower() in guild_names[gid].lower()
        ][:25]
        
        logger.debug(f"Returning {len(results)} guild autocomplete results")
        return results

    async def autocomplete_channel_id(interaction: discord.Interaction, current: str):
        logger.debug(f"autocomplete_channel_id called by {interaction.user.display_name} ({interaction.user.id}) with query: '{current}'")
        selected_guild_id = interaction.namespace.guild_id 
        try:
            with open("registered.json", "r") as f:
                data = json.load(f)
            logger.debug("Successfully loaded registered.json for channel autocomplete")
        except FileNotFoundError:
            logger.warning("registered.json not found for channel autocomplete")
            return []
        except Exception as e:
            logger.error(f"Error loading registered.json for channel autocomplete: {e}")
            return []

        channels = [entry for entry in data["register"] if entry["guild_id"] == selected_guild_id and entry['registrator_id'] == str(interaction.user.id)]

        results = []
        for entry in channels:
            guild = bot.get_guild(int(entry["guild_id"]))
            channel = guild.get_channel(int(entry["channel_id"])) if guild else None
            if channel:
                name = f"{channel.name} ({entry['channel_id']})"
            else:
                name = f"Channel {entry['channel_id']}"
            if current.lower() in name.lower():
                results.append(app_commands.Choice(name=name, value=entry["channel_id"]))

        logger.debug(f"Returning {len(results)} channel autocomplete results")
        return results[:25]

    async def autocomplete_remove_admin(interaction: discord.Interaction, current: str):
        logger.debug(f"autocomplete_remove_admin called by {interaction.user.display_name} ({interaction.user.id}) with query: '{current}'")
        try:
            data = helpers.load_roles()
            logger.debug("Successfully loaded roles data for admin autocomplete")
        except Exception as e:
            logger.error(f"Error loading roles data for admin autocomplete: {e}")
            return []

        admins = [entry for entry in data.get("admins", []) if entry["guild_id"] == str(interaction.guild.id)]
        results = []
        for entry in admins:
            name = f"{entry['user_name']} (ID: {entry['user_id']})"
            results.append(app_commands.Choice(name=name, value=entry["user_id"]))

        logger.debug(f"Returning {len(results)} admin autocomplete results")
        return results[:25]

    async def autocomplete_remove_registrator(interaction: discord.Interaction, current: str):
        logger.debug(f"autocomplete_remove_registrator called by {interaction.user.display_name} ({interaction.user.id}) with query: '{current}'")
        try:
            data = helpers.load_roles()
            logger.debug("Successfully loaded roles data for registrator autocomplete")
        except Exception as e:
            logger.error(f"Error loading roles data for registrator autocomplete: {e}")
            return []

        registrators = [entry for entry in data.get("registrators", []) if entry["guild_id"] == str(interaction.guild.id)]
        
        results = []
        for entry in registrators:
            name = f"{entry['user_name']} (ID: {entry['user_id']})"
            results.append(app_commands.Choice(name=name, value=entry["user_id"]))

        logger.debug(f"Returning {len(results)} registrator autocomplete results")
        return results[:25]

    async def autocomplete_group_name(interaction: discord.Interaction, current: str):
        logger.debug(f"autocomplete_group_name called by {interaction.user.display_name} ({interaction.user.id}) with query: '{current}'")
        
        try:
            linked_channels = helpers.load_linked_channels()
            logger.debug("Successfully loaded linked channels data for group autocomplete")
        except Exception as e:
            logger.error(f"Error loading linked channels data for group autocomplete: {e}")
            return []

        # Get all chanels registered by the user
        try:
            registered_channels = helpers.load_registered_channels()
            logger.debug("Successfully loaded registered channels data for group autocomplete")
        except Exception as e:
            logger.error(f"Error loading registered channels data for group autocomplete: {e}")
            return []
            
        user_registered_channels = [
            entry for entry in registered_channels["register"]
            if entry["registrator_id"] == str(interaction.user.id)
        ]
        
        # Check if any group of linked channels is already fully registered by the current user
        results = []
        for group in linked_channels["groups"]:
            channel_match = []
            
            # For each channel in the group's channel list
            for channel in group["channel_list"]:
                # Get guild ID of the channel
                guild_id = next((entry["guild_id"] for entry in group["links"] if entry["channel_id"] == channel), None)
                # Check if this channel is registered by the current user in the same guild
                if any(
                    entry["channel_id"] == channel and
                    entry["guild_id"] == guild_id and
                    entry["registrator_id"] == str(interaction.user.id)
                    for entry in user_registered_channels
                ):
                    channel_match.append(channel)
                # If not registered by user, skip it (implicitly)
            # If all channels in the group are registered by the current user
            if channel_match == group["channel_list"]:
                # And the group name matches the user's input (autocomplete)
                if current.lower() in group["group_name"].lower():
                    results.append(app_commands.Choice(name=group["group_name"], value=group["group_name"]))
        
        logger.debug(f"Returning {len(results)} group autocomplete results")
        return results[:25]

    # ------------------------------------------
    # Functions for slash commands
    # ------------------------------------------

    @bot.tree.command(name="register_channel", description="Register this channel for forwarding messages")
    async def register_channel(interaction: discord.Interaction):
        logger.info(f"register_channel command invoked by {interaction.user.display_name} ({interaction.user.id}) in guild {interaction.guild.name} ({interaction.guild.id}), channel {interaction.channel.name} ({interaction.channel.id})")
        
        # Load existing registered channels
        try:
            registered_channels = helpers.load_registered_channels()
            logger.debug("Successfully loaded registered channels data")
        except Exception as e:
            logger.error(f"Failed to load registered channels: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return
        
        # Check if the command is used in a text channel
        if interaction.channel.type != discord.ChannelType.text:
            logger.warning(f"register_channel command used in non-text channel: {interaction.channel.type}")
            await interaction.response.send_message("This command available for text channels only", ephemeral=True)
            return
        
        # Check if the user has permission to register the channel
        if not helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "register_channel"):
            logger.warning(f"User {interaction.user.display_name} ({interaction.user.id}) denied permission to register channel")
            await interaction.response.send_message("You have no permission to register channels for message forwarding.", ephemeral=True)
            return
        
        # Making an entry with guild_id and channel_id in registered.json
        guild_id = str(interaction.guild.id)
        guild_name = interaction.guild.name if interaction.guild else "Unknown Guild"
        channel_id = str(interaction.channel.id)

        # Check if the channel is already registered
        for entry in registered_channels["register"]:
            if entry["guild_id"] == guild_id and entry["channel_id"] == channel_id:
                logger.info(f"Channel {interaction.channel.name} ({channel_id}) already registered in guild {guild_name} ({guild_id})")
                await interaction.response.send_message("This channel is already registered for message forwarding.", ephemeral=True)
                return
            
        # Add new entry
        entry = {
            "guild_id": guild_id,   
            "guild_name": guild_name,
            "channel_id": channel_id,
            "channel_name": interaction.channel.name,
            "registrator_id": str(interaction.user.id),
            "registrator_name": interaction.user.display_name,
        }

        registered_channels["register"].append(entry)
        
        try:
            with open("registered.json", "w") as f:
                json.dump(registered_channels, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully registered channel {interaction.channel.name} ({channel_id}) by {interaction.user.display_name} ({interaction.user.id})")
        except Exception as e:
            logger.error(f"Failed to save registered channels data: {e}")
            await interaction.response.send_message("An error occurred while saving data.", ephemeral=True)
            return
            
        await interaction.response.send_message(f"Channel **{interaction.channel.name}** registered for message forwarding.", ephemeral=True)

        
    @bot.tree.command(name="show_registered_channels", description="Show registered channels for message forwarding")
    async def show_registered_channels(interaction: discord.Interaction):
        ''' Show all registered channels for message forwarding '''
        logger.info(f"show_registered_channels command invoked by {interaction.user.display_name} ({interaction.user.id}) in guild {interaction.guild.name} ({interaction.guild.id})")
        
        try:
            registered_channels = helpers.load_registered_channels()
            logger.debug("Successfully loaded registered channels data")
        except Exception as e:
            logger.error(f"Failed to load registered channels: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        # Check if there are any registered channels
        if not registered_channels["register"]:
            logger.debug("No registered channels found")
            await interaction.response.send_message("No channels registered for message forwarding.", ephemeral=True)
            return
        
        # Check if the user is superadmin or admin
        is_superadmin = helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "superadmin_only")
        is_admin = helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "admin_only")
        
        if not is_superadmin and not is_admin:
            logger.debug(f"User {interaction.user.display_name} is not admin/superadmin, filtering channels by registrator")
            # Filter registered channels by the registrator id
            registrator_id = str(interaction.user.id)
            registered_channels["register"] = [
                entry for entry in registered_channels["register"]
                if entry["registrator_id"] == registrator_id
            ]

            # If no channels are registered by the user
            if not registered_channels["register"]:
                logger.debug(f"No channels registered by user {interaction.user.display_name} ({interaction.user.id})")
                await interaction.response.send_message("You have no registered channels for message forwarding.", ephemeral=True)
                return
        else:
            logger.debug(f"User {interaction.user.display_name} is admin/superadmin, showing all channels")

        # Create a message with all registered channels
        msg = "Registered channels for message forwarding:\n"
        channel_count = 0
        for entry in registered_channels["register"]:
            guild = bot.get_guild(int(entry["guild_id"]))
            channel = guild.get_channel(int(entry["channel_id"])) if guild else None
            if channel:
                msg += (
                    f"→ Guild: {guild.name} | Channel: {channel.name}\n"
                    f"(Guild ID: {entry['guild_id']}, Channel_id: {entry['channel_id']})\n\n"
                )
                channel_count += 1
            else:
                msg += f"→ Guild ID: {entry['guild_id']} | Channel ID: {entry['channel_id']} (Channel not found)\n\n"
                channel_count += 1
        
        logger.info(f"Displayed {channel_count} registered channels to {interaction.user.display_name} ({interaction.user.id})")
        await interaction.response.send_message(msg, ephemeral=True)


    @bot.tree.command(name="link_channel", description="Link this channel with another server's channel")
    @app_commands.describe(
        guild_id="Target server's guild ID",
        target_channel_id="Target server's channel ID",
        group_name="Name of the linked channels group")

    @app_commands.autocomplete(
        guild_id=autocomplete_guild_id,
        target_channel_id=autocomplete_channel_id)

    async def link_channel(interaction: discord.Interaction, guild_id: str, target_channel_id: str, group_name: str):
        '''Link this channel with specified guild and channel'''

        logger.info(f"link_channel command invoked by {interaction.user.display_name} ({interaction.user.id}) in guild {interaction.guild.name} ({interaction.guild.id}), target guild: {guild_id}, target channel: {target_channel_id}, group: {group_name}")

        try:
            registered_channels = commands_helpers.load_registered_channels()
            logger.debug("Successfully loaded registered channels data")
        except Exception as e:
            logger.error(f"Failed to load registered channels: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        # Permission check
        if not commands_helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "link_channel"):
            logger.warning(f"User {interaction.user.display_name} ({interaction.user.id}) denied permission to link channel")
            await interaction.response.send_message("You have no permission to link channels for message forwarding.", ephemeral=True)
            return

        if not await commands_helpers.is_channel_registered(registered_channels, str(interaction.guild.id), str(interaction.channel.id)):
            logger.warning(f"Current channel {interaction.channel.name} ({interaction.channel.id}) is not registered")
            await interaction.response.send_message("This channel is not registered for message forwarding.", ephemeral=True)
            return

        if not await commands_helpers.is_channel_registered_by_user(registered_channels, interaction):
            logger.warning(f"Current channel {interaction.channel.name} ({interaction.channel.id}) is not registered by user {interaction.user.display_name} ({interaction.user.id})")
            await interaction.response.send_message("You can only link channels that you have registered.", ephemeral=True)
            return

        if not await commands_helpers.is_channel_registered(registered_channels, guild_id, target_channel_id):
            logger.warning(f"Target channel {target_channel_id} in guild {guild_id} is not registered")
            await interaction.response.send_message("Target channel is not registered for message forwarding.", ephemeral=True)
            return

        if not await commands_helpers.is_channel_registered_by_user_id(registered_channels, guild_id, target_channel_id, str(interaction.user.id)):
            logger.warning(f"Target channel {target_channel_id} in guild {guild_id} is not registered by user {interaction.user.display_name} ({interaction.user.id})")
            await interaction.response.send_message("You can only link channels that you have registered.", ephemeral=True)
            return

        # Get target guild and channel
        target_guild = bot.get_guild(int(guild_id))
        target_channel = target_guild.get_channel(int(target_channel_id)) if target_guild else None

        # Create infinite invite links
        current_invite_url = await commands_helpers.create_invite(interaction.channel)
        target_invite_url = await commands_helpers.create_invite(target_channel)

        # Load existing links
        try:
            linked_channels = commands_helpers.load_linked_channels()
        except Exception as e:
            logger.error(f"Failed to load linked channels: {e}")
            await interaction.response.send_message("An error occurred while loading linked channels data.", ephemeral=True)
            return

        # Form current and target entries with invite links
        current_entry = {
            "channel_id": str(interaction.channel.id),
            "channel_name": str(interaction.channel.name),
            "guild_id": str(interaction.guild.id),
            "guild_name": interaction.guild.name if interaction.guild else "Unknown Guild",
            "invite_url": current_invite_url
        }

        target_entry = {
            "channel_id": target_channel_id,
            "channel_name": target_channel.name if target_channel else "Unknown Channel",
            "guild_id": guild_id,
            "guild_name": target_guild.name if target_guild else "Unknown Server",
            "invite_url": target_invite_url
        }

        # Check if target data is the same as current data
        if current_entry["guild_id"] == target_entry["guild_id"] and current_entry["channel_id"] == target_entry["channel_id"]:
            logger.warning(f"User {interaction.user.display_name} tried to link channel to itself")
            await interaction.response.send_message("You cannot link a channel to itself.", ephemeral=True)
            return

        # Check if already linked or in any group
        if commands_helpers.is_channel_already_linked(current_entry["channel_id"], target_entry["channel_id"], linked_channels):
            logger.warning(f"Channels {current_entry['channel_id']} and {target_entry['channel_id']} are already linked")
            await interaction.response.send_message("This channel is already linked with the target channel.", ephemeral=True)
            return

        if commands_helpers.is_channel_in_any_group(current_entry["channel_id"], linked_channels) or commands_helpers.is_channel_in_any_group(target_entry["channel_id"], linked_channels):
            logger.warning(f"One of the channels ({current_entry['channel_id']} or {target_entry['channel_id']}) is already part of a group")
            await interaction.response.send_message("One of the channels is already part of a group.", ephemeral=True)
            return

        # Add a new group with the two channels
        commands_helpers.add_new_linked_group(linked_channels, group_name, current_entry, target_entry)
        try:
            commands_helpers.save_json_file("linked_channels.json", linked_channels)
            logger.info(f"Successfully created new link group '{group_name}' with channels {[current_entry['channel_id'], target_entry['channel_id']]}")
        except Exception as e:
            logger.error(f"Failed to save linked channels data: {e}")
            await interaction.response.send_message("An error occurred while saving link data.", ephemeral=True)
            return

        # Remove the current channel and target channel from registered.json if it is linked
        try:
            commands_helpers.remove_channels_from_registered(registered_channels, [str(interaction.channel.id), target_channel_id], [str(interaction.guild.id), guild_id])
            commands_helpers.save_json_file("registered.json", registered_channels)
            logger.info(f"Removed linked channels from registered.json")
        except Exception as e:
            logger.error(f"Failed to update registered.json after linking: {e}")

        # Remove the user from temporary registrators if they are one
        commands_helpers.remove_registrator(str(interaction.user.id), str(interaction.guild.id))
        logger.debug(f"Removed user {interaction.user.display_name} from temporary registrators")

        await interaction.response.send_message(
            f"Channel **{interaction.channel.name}** linked with **{target_channel.name if target_channel else 'Unknown'}** in **{target_guild.name if target_guild else 'Unknown'}**.",
            ephemeral=True
        )

    @bot.tree.command(name="show_linked_channels", description="Show linked servers and channels with this channel")
    async def linked_channels(interaction: discord.Interaction):
        '''Show linked servers and channels with this channel'''
        logger.info(f"show_linked_channels command invoked by {interaction.user.display_name} ({interaction.user.id}) in guild {interaction.guild.name} ({interaction.guild.id}), channel {interaction.channel.name} ({interaction.channel.id})")
        
        try:
            linked_channels = helpers.load_linked_channels()
        except Exception as e:
            logger.error(f"Failed to load linked channels: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        current_guild_id = str(interaction.guild.id)
        current_channel_id = str(interaction.channel.id)

        # Find the group containing the current channel
        for group in linked_channels["groups"]:
            if any(link["guild_id"] == current_guild_id and link["channel_id"] == current_channel_id for link in group["links"]):
                logger.debug(f"Found linked group '{group['group_name']}' for channel {interaction.channel.name}")
                msg = f"Linked channels for **{interaction.channel.name}** in group **{group['group_name']}**:\n"

                for link in group["links"]:
                    # # Skip the current channel
                    if link["guild_id"] == current_guild_id and link["channel_id"] == current_channel_id:
                        msg += f"→ This channel: Guild: {interaction.guild.name} | Channel: {interaction.channel.name}\n"
                        continue

                    # Try to get guild and channel objects
                    guild = bot.get_guild(int(link["guild_id"]))
                    channel = guild.get_channel(int(link["channel_id"])) if guild else None

                    if channel:
                        msg += f"→ Guild: {guild.name} | Channel: {channel.name}\n"
                    else:
                        msg += f"→ Guild ID: {link['guild_id']} | Channel ID: {link['channel_id']} (Channel not found)\n"

                await interaction.response.send_message(msg, ephemeral=True)
                return

        logger.debug(f"Channel {interaction.channel.name} ({current_channel_id}) is not linked to any other channels")
        await interaction.response.send_message("This channel is not linked to any other channels.", ephemeral=True)

    @bot.tree.command(name="unlink_channel", description="Unlink this channel from group of linked channels")
    async def unlink(interaction: discord.Interaction):
        '''Unlink this channel from group of linked channels'''
        logger.info(f"unlink_channel command invoked by {interaction.user.display_name} ({interaction.user.id}) in guild {interaction.guild.name} ({interaction.guild.id}), channel {interaction.channel.name} ({interaction.channel.id})")
        
        try:
            linked_channels = helpers.load_linked_channels()
        except Exception as e:
            logger.error(f"Failed to load linked channels: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return
        
        # Check if the user has permission to unlink the channel
        if not helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "unlink_channel"):
            logger.warning(f"User {interaction.user.display_name} ({interaction.user.id}) denied permission to unlink channel")
            await interaction.response.send_message("You have no permission to unlink channels", ephemeral=True)
            return

        # Check if the current channel is part of any link group
        if not any(link["guild_id"] == str(interaction.guild.id) and link["channel_id"] == str(interaction.channel.id) for group in linked_channels["groups"] for link in group["links"]):
            logger.warning(f"Channel {interaction.channel.name} ({interaction.channel.id}) is not linked to any other channels")
            await interaction.response.send_message("This channel is not linked to any other channels.", ephemeral=True)
            return

        # Find the group containing the current channel
        for group in linked_channels["groups"]:
            for link in group["links"]:
                if link["guild_id"] == str(interaction.guild.id) and link["channel_id"] == str(interaction.channel.id):
                    group["links"].remove(link)
                    group["channel_list"].remove(str(interaction.channel.id))
                    
                    if len(group["links"]) == 1:
                        linked_channels["groups"].remove(group)
                        logger.info(f"Removed group '{group['group_name']}' as it only had one channel left")
                    
                    try:
                        with open("linked_channels.json", "w") as f:
                            json.dump(linked_channels, f, indent=4, ensure_ascii=False)
                        logger.info(f"Successfully unlinked channel {interaction.channel.name} ({interaction.channel.id}) from group")
                    except Exception as e:
                        logger.error(f"Failed to save linked channels data after unlinking: {e}")
                        await interaction.response.send_message("An error occurred while saving data.", ephemeral=True)
                        return
                    
                    await interaction.response.send_message(
                        f"Channel **{interaction.channel.name}** unlinked from the group.",
                        ephemeral=True
                    )
                    return

    @bot.tree.command(name="remove_channel_registration", description="Remove this channel from registered channels")
    async def remove_registration(interaction: discord.Interaction):
        '''Remove this channel from registered channels'''
        logger.info(f"remove_channel_registration command invoked by {interaction.user.display_name} ({interaction.user.id}) in guild {interaction.guild.name} ({interaction.guild.id}), channel {interaction.channel.name} ({interaction.channel.id})")
        
        try:
            registered_channels = helpers.load_registered_channels()
            logger.debug("Successfully loaded registered channels data")
        except Exception as e:
            logger.error(f"Failed to load registered channels: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        # Check if the user has permission to remove channel registration
        if not helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "remove_channel_registration"):
            logger.warning(f"User {interaction.user.display_name} ({interaction.user.id}) denied permission to remove channel registration")
            await interaction.response.send_message("You have no permission to remove channel registration.", ephemeral=True)
            return
        
        # Check if the channel is registered
        if not any(
            entry["guild_id"] == str(interaction.guild.id) and entry["channel_id"] == str(interaction.channel.id)
            for entry in registered_channels["register"]
        ):
            logger.warning(f"Channel {interaction.channel.name} ({interaction.channel.id}) is not registered")
            await interaction.response.send_message("This channel is not registered for message forwarding.", ephemeral=True)
            return

        # Remove the channel from registered channels
        registered_channels["register"] = [
            entry for entry in registered_channels["register"]
            if not (entry["guild_id"] == str(interaction.guild.id) and entry["channel_id"] == str(interaction.channel.id))
        ]   
        
        try:
            with open("registered.json", "w") as f:
                json.dump(registered_channels, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully removed channel {interaction.channel.name} ({interaction.channel.id}) from registered channels")
        except Exception as e:
            logger.error(f"Failed to save registered channels data after removal: {e}")
            await interaction.response.send_message("An error occurred while saving data.", ephemeral=True)
            return

        await interaction.response.send_message("This channel has been removed from registered channels.", ephemeral=True)

    @bot.tree.command(name="set_admin", description="Set a user as admin for this bot in this server")
    async def set_admin(interaction: discord.Interaction, user: discord.User):
        '''Set a user as admin for this bot in this server'''
        logger.info(f"set_admin command invoked by {interaction.user.display_name} ({interaction.user.id}) to set {user.display_name} ({user.id}) as admin in guild {interaction.guild.name} ({interaction.guild.id})")
        
        try:
            data = helpers.load_roles()
            logger.debug("Successfully loaded roles data")
        except Exception as e:
            logger.error(f"Failed to load roles data: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        # Check if the user has a role of SuperAdmin
        if helpers.has_user_permission(str(user.id), str(interaction.guild.id), "can't_be_admin"):   
            logger.warning(f"Cannot set {user.display_name} ({user.id}) as admin - user can't be admin")
            return await interaction.response.send_message("You cannot set a yourself as an admin.", ephemeral=True)

        # Check if the user has permission to set admin
        if not helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "set_admin"):
            logger.warning(f"User {interaction.user.display_name} ({interaction.user.id}) denied permission to set admin")
            await interaction.response.send_message("You have no permission to set admins", ephemeral=True)
            return
        
        # Check if the user is already an admin of this bot in this server
        user_id = str(user.id)
        user_name = user.display_name
        guild_id = str(interaction.guild.id)
        guild_name = interaction.guild.name if interaction.guild else "Unknown Guild"

        if any(entry["user_id"] == user_id and entry["guild_id"] == guild_id for entry in data.get("admins", [])):
            logger.info(f"User {user.display_name} ({user.id}) is already an admin in guild {guild_name} ({guild_id})")
            return await interaction.response.send_message("You are already an admin of this bot in this server.", ephemeral=True)
        
        # Add the user as an admin
        new_admin = {
            "user_id": user_id,
            "user_name": user_name,
            "guild_id": guild_id,
            "guild_name": guild_name
        }

        data["admins"].append(new_admin)

        try:
            with open("roles.json", "w") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully set {user.display_name} ({user.id}) as admin in guild {guild_name} ({guild_id})")
        except Exception as e:
            logger.error(f"Failed to save roles data: {e}")
            await interaction.response.send_message("An error occurred while saving data.", ephemeral=True)
            return

        return await interaction.response.send_message(
            f"User **{user_name}** has been set as an admin for this bot in this server.",
            ephemeral=True
        )

    @bot.tree.command(name="set_superadmin", description="Set a user as superadmin for this bot in this server")
    async def set_superadmin(interaction: discord.Interaction):
        '''Set a user as superadmin for this bot'''
        logger.info(f"set_superadmin command invoked by {interaction.user.display_name} ({interaction.user.id}) in guild {interaction.guild.name} ({interaction.guild.id})")

        # Check if user is administrator of the server
        if not interaction.user.guild_permissions.administrator:
            logger.warning(f"User {interaction.user.display_name} ({interaction.user.id}) is not a server administrator")
            return await interaction.response.send_message("You must be an administrator of this server to use this command.", ephemeral=True)

        try:
            roles_data = helpers.load_roles()
            logger.debug("Successfully loaded roles data")
        except Exception as e:
            logger.error(f"Failed to load roles data: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        # Check if the user is already a superadmin of this bot in this server
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        if any(entry["user_id"] == user_id and entry["guild_id"] == guild_id for entry in roles_data.get("superadmins", [])):
            logger.info(f"User {interaction.user.display_name} ({user_id}) is already a superadmin in guild {interaction.guild.name} ({guild_id})")
            return await interaction.response.send_message("You are already a superadmin of this bot in this server.", ephemeral=True)

        # Check if there is already a superadmin in this server
        if any(entry["guild_id"] == guild_id for entry in roles_data.get("superadmins", [])):
            logger.warning(f"Guild {interaction.guild.name} ({guild_id}) already has a superadmin")
            return await interaction.response.send_message("There is already a superadmin for this bot in this server.", ephemeral=True)

        # Add the user as a superadmin
        new_superadmin = {
            "user_id": user_id,
            "user_name": interaction.user.display_name,
            "guild_id": str(interaction.guild.id),
            "guild_name": interaction.guild.name if interaction.guild else "Unknown Guild"
        }

        roles_data["superadmins"].append(new_superadmin)

        try:
            with open("roles.json", "w") as f:
                json.dump(roles_data, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully set {interaction.user.display_name} ({user_id}) as superadmin in guild {interaction.guild.name} ({guild_id})")
        except Exception as e:
            logger.error(f"Failed to save roles data: {e}")
            await interaction.response.send_message("An error occurred while saving data.", ephemeral=True)
            return

        return await interaction.response.send_message(
            f"User **{interaction.user.display_name}** has been set as a superadmin for this bot in this server.",
            ephemeral=True
        )

    @bot.tree.command(name="show_admins", description="Show all admins of this bot in this server")
    async def set_ashow_adminsdmin(interaction: discord.Interaction):
        '''Show all admins of this bot in this server'''
        logger.info(f"show_admins command invoked by {interaction.user.display_name} ({interaction.user.id}) in guild {interaction.guild.name} ({interaction.guild.id})")
        
        try:
            roles_data = helpers.load_roles()
            logger.debug("Successfully loaded roles data")
        except Exception as e:
            logger.error(f"Failed to load roles data: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        admins = [entry for entry in roles_data.get("admins", []) if entry["guild_id"] == guild_id]

        if not admins:
            logger.debug(f"No admins found for guild {interaction.guild.name} ({guild_id})")
            return await interaction.response.send_message("No admins found for this bot in this server.", ephemeral=True)

        msg = "Admins of this bot in this server:\n"
        for admin in admins:
            msg += f"→ **{admin['user_name']}** (ID: {admin['user_id']})\n"

        logger.info(f"Displayed {len(admins)} admins to {interaction.user.display_name} ({interaction.user.id})")
        await interaction.response.send_message(msg, ephemeral=True)

    @bot.tree.command(name="set_registrator", description="Set a user as one-time registrator for this bot in this server")
    async def set_registrator(interaction: discord.Interaction, user: discord.User):
        '''Set a user as temporary registrator for this bot in this server'''
        logger.info(f"set_registrator command invoked by {interaction.user.display_name} ({interaction.user.id}) to set {user.display_name} ({user.id}) as registrator in guild {interaction.guild.name} ({interaction.guild.id})")

        # SuperAdmins and Admins can't set themselfes as registrators
        if helpers.has_user_permission(str(user.id), str(interaction.guild.id), "can't_be_registrator"):
            logger.warning(f"Cannot set {user.display_name} ({user.id}) as registrator - user can't be registrator")
            return await interaction.response.send_message("You cannot set yourself as a registrator.", ephemeral=True)
        
        # Only SuperAdmins and Admins can set registrators
        if not helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "set_registrator"):
            logger.warning(f"User {interaction.user.display_name} ({interaction.user.id}) denied permission to set registrator")
            await interaction.response.send_message("You have no permission to set registrators", ephemeral=True)
            return
        
        # Check if the user is already a registrator of this bot in this server
        user_id = str(user.id)
        guild_id = str(interaction.guild.id)
        
        try:
            roles_data = helpers.load_roles()
            logger.debug("Successfully loaded roles data")
        except Exception as e:
            logger.error(f"Failed to load roles data: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return
        
        if any(entry["user_id"] == user_id and entry["guild_id"] == guild_id for entry in roles_data.get("registrators", [])):
            logger.info(f"User {user.display_name} ({user.id}) is already a registrator in guild {interaction.guild.name} ({guild_id})")
            return await interaction.response.send_message("This user is already a registrator of this bot in this server.", ephemeral=True)

        # Format registrator data
        reg = {
            "user_id": str(user.id),
            "user_name": user.name,
            "guild_id": str(interaction.guild.id),
            "guild_name": interaction.guild.name if interaction.guild else "Unknown Guild"
        }

        # Add the new registrator
        roles_data["registrators"].append(reg)

        try:
            with open("roles.json", "w") as f:
                json.dump(roles_data, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully set {user.display_name} ({user.id}) as registrator in guild {interaction.guild.name} ({guild_id})")
        except Exception as e:
            logger.error(f"Failed to save roles data: {e}")
            await interaction.response.send_message("An error occurred while saving data.", ephemeral=True)
            return

        await interaction.response.send_message(f"**{user.name}** has been set as a one-time registrator for this bot in this server.", ephemeral=True)

    @bot.tree.command(name="remove_admin", description="Remove a user from admins of this bot in this server")
    @app_commands.describe(
        user_id="User to remove from admins")

    @app_commands.autocomplete(
        user_id = autocomplete_remove_admin)

    async def remove_admin(interaction: discord.Interaction, user_id: str):
        '''Remove a user from admins of this bot in this server'''
        logger.info(f"remove_admin command invoked by {interaction.user.display_name} ({interaction.user.id}) to remove user {user_id} from admins in guild {interaction.guild.name} ({interaction.guild.id})")

        # Check if the user has permission to remove admins
        if not helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "remove_admin"):
            logger.warning(f"User {interaction.user.display_name} ({interaction.user.id}) denied permission to remove admin")
            await interaction.response.send_message("You have no permission to remove admins", ephemeral=True)
            return

        try:
            roles_data = helpers.load_roles()
            logger.debug("Successfully loaded roles data")
        except Exception as e:
            logger.error(f"Failed to load roles data: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        # Get user by ID
        try:
            user = interaction.guild.get_member(int(user_id)) or await interaction.guild.fetch_member(int(user_id))
        except discord.NotFound:
            logger.warning(f"User {user_id} not found in guild {interaction.guild.name} ({guild_id})")
            return await interaction.response.send_message("User not found in this server.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return await interaction.response.send_message("An error occurred while fetching user data.", ephemeral=True)

        # Remove user from admins
        original_count = len(roles_data.get("admins", []))
        roles_data["admins"] = [admin for admin in roles_data.get("admins", []) if not (admin["user_id"] == user_id and admin["guild_id"] == guild_id)]
        
        if len(roles_data["admins"]) == original_count:
            logger.warning(f"User {user.name} ({user_id}) was not an admin in guild {interaction.guild.name} ({guild_id})")
            await interaction.response.send_message("User was not found in the admin list.", ephemeral=True)
            return

        try:
            with open("roles.json", "w") as f:
                json.dump(roles_data, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully removed {user.name} ({user_id}) from admins in guild {interaction.guild.name} ({guild_id})")
        except Exception as e:
            logger.error(f"Failed to save roles data: {e}")
            await interaction.response.send_message("An error occurred while saving data.", ephemeral=True)
            return

        await interaction.response.send_message(f"**{user.name}** (ID:**{user.id}**) has been removed from admins of this bot in this server.", ephemeral=True)

    @bot.tree.command(name="remove_registrator", description="Remove a user from temporary registrators of this bot in this server")
    @app_commands.describe(
        user_id="User to remove from temporary registrators")

    @app_commands.autocomplete(
        user_id = autocomplete_remove_registrator)

    async def remove_registrator(interaction: discord.Interaction, user_id: str):
        '''Remove a user from temporary registrators of this bot in this server'''
        logger.info(f"remove_registrator command invoked by {interaction.user.display_name} ({interaction.user.id}) to remove user {user_id} from registrators in guild {interaction.guild.name} ({interaction.guild.id})")
        
        # Check if the user has permission to remove registrators
        if not helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "remove_registrator"):
            logger.warning(f"User {interaction.user.display_name} ({interaction.user.id}) denied permission to remove registrator")
            await interaction.response.send_message("You have no permission to remove registrators", ephemeral=True)
            return
        
        try:
            roles_data = helpers.load_roles()
            logger.debug("Successfully loaded roles data")
        except Exception as e:
            logger.error(f"Failed to load roles data: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        # Get user by ID
        try:
            user = interaction.guild.get_member(int(user_id)) or await interaction.guild.fetch_member(int(user_id))
        except discord.NotFound:
            logger.warning(f"User {user_id} not found in guild {interaction.guild.name} ({guild_id})")
            return await interaction.response.send_message("User not found in this server.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return await interaction.response.send_message("An error occurred while fetching user data.", ephemeral=True)

        # Remove user from registrators
        original_count = len(roles_data.get("registrators", []))
        roles_data["registrators"] = [reg for reg in roles_data.get("registrators", []) if not (reg["user_id"] == user_id and reg["guild_id"] == guild_id)]
        
        if len(roles_data["registrators"]) == original_count:
            logger.warning(f"User {user.name} ({user_id}) was not a registrator in guild {interaction.guild.name} ({guild_id})")
            await interaction.response.send_message("User was not found in the registrator list.", ephemeral=True)
            return
        
        try:
            with open("roles.json", "w") as f:
                json.dump(roles_data, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully removed {user.name} ({user_id}) from registrators in guild {interaction.guild.name} ({guild_id})")
        except Exception as e:
            logger.error(f"Failed to save roles data: {e}")
            await interaction.response.send_message("An error occurred while saving data.", ephemeral=True)
            return
        
        await interaction.response.send_message(f"**{user.name}** (ID:**{user.id}**) has been removed from temporary registrators of this bot in this server.", ephemeral=True)

    @bot.tree.command(name="link_channel_to_group", description="Link a channel to an existing group of linked channels")
    @app_commands.describe(
        group_name="Name of the group to link this channel to")

    @app_commands.autocomplete(
        group_name = autocomplete_group_name)

    async def link_channel_to_group(interaction: discord.Interaction, group_name: str):
        '''Link a channel to an existing group of linked channels'''
        logger.info(f"link_channel_to_group command invoked by {interaction.user.display_name} ({interaction.user.id}) in guild {interaction.guild.name} ({interaction.guild.id}), channel {interaction.channel.name} ({interaction.channel.id}), group: {group_name}")

        # Permission check
        if not commands_helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "link_channel"):
            logger.warning(f"User {interaction.user.display_name} ({interaction.user.id}) denied permission to link channel to group")
            await interaction.response.send_message("You have no permission to link channels to groups", ephemeral=True)
            return

        # Load registered channels data
        try:
            registered_data = commands_helpers.load_registered_channels()
            logger.debug("Successfully loaded registered channels data")
        except Exception as e:
            logger.error(f"Failed to load registered channels: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        # Load linked channels data
        try:
            linked_channels = commands_helpers.load_linked_channels()
        except Exception as e:
            logger.error(f"Failed to load linked channels: {e}")
            await interaction.response.send_message("An error occurred while loading linked channels data.", ephemeral=True)
            return

        # Check if the current channel is registered and registered by the user
        if not await commands_helpers.is_channel_registered(registered_data, str(interaction.guild.id), str(interaction.channel.id)):
            logger.warning(f"Channel {interaction.channel.name} ({interaction.channel.id}) is not registered")
            await interaction.response.send_message("This channel is not registered for message forwarding.", ephemeral=True)
            return

        if not await commands_helpers.is_channel_registered_by_user(registered_data, interaction):
            logger.warning(f"Channel {interaction.channel.name} ({interaction.channel.id}) is not registered by user {interaction.user.display_name} ({interaction.user.id})")
            await interaction.response.send_message("You can only link channels that you have registered.", ephemeral=True)
            return

        # Check if the current channel is already part of any other group
        if commands_helpers.is_channel_in_any_group(str(interaction.channel.id), linked_channels):
            logger.warning(f"Channel {interaction.channel.name} ({interaction.channel.id}) is already linked to another group.")
            await interaction.response.send_message(
                f"This channel is already linked to another group.",
                ephemeral=True
            )
            return

        # Find the specified group
        group = commands_helpers.get_group_by_name(linked_channels, group_name)
        if not group:
            logger.warning(f"No group found with name '{group_name}'")
            await interaction.response.send_message(f"No group found with name **{group_name}**.", ephemeral=True)
            return

        # Verify that all channels in the group are registered by the user
        not_all_registered, not_registered_link = await commands_helpers.are_all_group_channels_registered_by_user(group, registered_data, str(interaction.user.id))
        if not_all_registered:
            logger.warning(f"Channel {not_registered_link['channel_name']} from {not_registered_link['guild_name']} in group {group_name} is not registered by user {interaction.user.display_name}")
            await interaction.response.send_message(
                f"Channel **{not_registered_link['channel_name']}** from server **{not_registered_link['guild_name']}** in group **{group_name}** is not registered or registered by another user.",
                ephemeral=True
            )
            return

        # Generate invite link for the current channel
        try:
            invite_url = await commands_helpers.create_invite(interaction.channel)
            logger.debug(f"Generated invite link for channel {interaction.channel.name} ({interaction.channel.id})")
        except Exception as e:
            logger.error(f"Failed to generate invite link for channel {interaction.channel.name} ({interaction.channel.id}): {e}")
            invite_url = None

        # Add the current channel to the group's links
        current_entry = {
            "channel_id": str(interaction.channel.id),
            "channel_name": interaction.channel.name,
            "guild_id": str(interaction.guild.id),
            "guild_name": interaction.guild.name if interaction.guild else "Unknown Guild",
            "invite_url": invite_url
        }

        group["links"].append(current_entry)
        group["channel_list"].append(current_entry["channel_id"])

        try:
            commands_helpers.save_json_file("linked_channels.json", linked_channels)
            logger.info(f"Successfully linked channel {interaction.channel.name} ({interaction.channel.id}) to group '{group_name}'")
        except Exception as e:
            logger.error(f"Failed to save linked channels data: {e}")
            await interaction.response.send_message("An error occurred while saving data.", ephemeral=True)
            return

        # Remove the user from temporary registrators if they are one
        commands_helpers.remove_registrator(str(interaction.user.id), str(interaction.guild.id))
        logger.debug(f"Removed user {interaction.user.display_name} from temporary registrators")

        # Remove all group channels from registered.json
        for cid in group["channel_list"]:
            registered_data["register"] = [
                entry for entry in registered_data["register"]
                if not (entry["channel_id"] == cid)
            ]

        try:
            commands_helpers.save_json_file("registered.json", registered_data)
            logger.info(f"Removed all group channels from registered.json for group '{group_name}'")
        except Exception as e:
            logger.error(f"Failed to update registered channels after linking to group: {e}")

        await interaction.response.send_message(
            f"Channel **{interaction.channel.name}** has been linked to the group **{group_name}**.",
            ephemeral=True
        )

    @bot.tree.command(name="set_my_avatar", description="Set an emoji as your avatar for bridged messages")
    @app_commands.describe(emoji="The emoji you want to use as your avatar")
    async def set_my_avatar(interaction: discord.Interaction, emoji: str):
        '''Set an emoji as your avatar for bridged messages'''
        logger.info(f"set_my_avatar command invoked by {interaction.user.display_name} ({interaction.user.id}) with emoji: {emoji}")

        # Validate that the input is a single emoji (Unicode or Discord custom emoji)
        if not helpers.validate_single_emoji(emoji):
            await interaction.response.send_message("Please provide only one emoji as your avatar.", ephemeral=True)
            return
        
        try:
            # Set the user's avatar in the database
            database.set_user_avatar(str(interaction.user.id), emoji)
            logger.info(f"Successfully set avatar {emoji} for user {interaction.user.display_name} ({interaction.user.id})")
            
            await interaction.response.send_message(
                f"Your avatar has been set to {emoji}! This emoji will now appear in the header of your bridged messages.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Failed to set avatar for user {interaction.user.display_name} ({interaction.user.id}): {e}")
            await interaction.response.send_message("An error occurred while setting your avatar. Please try again.", ephemeral=True)

    @bot.tree.command(name="remove_my_avatar", description="Remove your custom avatar and use random emoji instead")
    async def remove_my_avatar(interaction: discord.Interaction):
        '''Remove your custom avatar and use random emoji instead'''
        logger.info(f"remove_my_avatar command invoked by {interaction.user.display_name} ({interaction.user.id})")

        try:
            import database
            # Check if user has an avatar to remove
            current_avatar = database.get_user_avatar(str(interaction.user.id))
            if not current_avatar:
                await interaction.response.send_message("You don't have a custom avatar set.", ephemeral=True)
                return
            
            # Remove the user's avatar from the database
            success = database.delete_user_avatar(str(interaction.user.id))
            if success:
                logger.info(f"Successfully removed avatar for user {interaction.user.display_name} ({interaction.user.id})")
                await interaction.response.send_message(
                    "Your custom avatar has been removed. Default emoji will now be used in your bridged messages.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("Failed to remove your avatar. Please try again.", ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to remove avatar for user {interaction.user.display_name} ({interaction.user.id}): {e}")
            await interaction.response.send_message("An error occurred while removing your avatar. Please try again.", ephemeral=True)

    @bot.tree.command(name="show_my_avatar", description="Show your current avatar emoji")
    async def show_my_avatar(interaction: discord.Interaction):
        '''Show your current avatar emoji'''
        logger.info(f"show_my_avatar command invoked by {interaction.user.display_name} ({interaction.user.id})")

        try:
            import database
            # Get the user's current avatar
            user_avatar = database.get_user_avatar(str(interaction.user.id))
            if user_avatar:
                await interaction.response.send_message(
                    f"Your current avatar is: {user_avatar}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "You don't have a custom avatar set. The default emoji is being used for your bridged messages.",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Failed to get avatar for user {interaction.user.display_name} ({interaction.user.id}): {e}")
            await interaction.response.send_message("An error occurred while retrieving your avatar. Please try again.", ephemeral=True)

    @bot.tree.command(name="get_invites", description="Get invite links for all linked channels in the same group as this channel")
    async def get_invites(interaction: discord.Interaction):
        '''Get invite links for all linked channels in the same group as this channel.'''

        logger.info(f"get_invites command invoked by {interaction.user.display_name} ({interaction.user.id}) in guild {interaction.guild.name} ({interaction.guild.id}), channel {interaction.channel.name} ({interaction.channel.id})")

        try:
            linked_channels = commands_helpers.load_linked_channels()
        except Exception as e:
            logger.error(f"Failed to load linked channels: {e}")
            await interaction.response.send_message("An error occurred while loading linked channels data.", ephemeral=True)
            return

        current_channel_id = str(interaction.channel.id)
        found_group = None
        for group in linked_channels.get("groups", []):
            if current_channel_id in group.get("channel_list", []):
                found_group = group
                break

        if not found_group:
            logger.info(f"No linked group found for channel {interaction.channel.name} ({current_channel_id})")
            await interaction.response.send_message("This channel is not linked to any other channels.", ephemeral=True)
            return

        msg = f"Invite links for linked channels in group **{found_group['group_name']}**:\n"
        for link in found_group.get("links", []):
            invite_url = link.get("invite_url")
            if invite_url:
                msg += f"→ [{link.get('guild_name')}]({invite_url}) | #**{link.get('channel_name')}**\n"
            else:
                msg += f"→ [{link.get('guild_name')}] | #**{link.get('channel_name')}** (No invite found)\n"

        await interaction.response.send_message(msg)