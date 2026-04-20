from discord import app_commands
from discord.ext import commands
import discord
import json
import re
from roles import SuperAdmin, Admin, Registrator
import helpers
from logger_config import get_logger
import database
import commands_helpers

# Set up logger for commands module
logger = get_logger(__name__)


def setup(bot):
    def format_guild_display_name(guild: discord.Guild | None, fallback_name: str) -> str:
        if guild:
            return guild.name

        # Strip stale IDs from persisted names like "Server Name(123456789012345678)".
        return re.sub(r"\s*\(\d{10,}\)\s*$", "", fallback_name).strip() or fallback_name

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

    async def autocomplete_source_channel_id(interaction: discord.Interaction, current: str):
        logger.debug(f"autocomplete_source_channel_id called by {interaction.user.display_name} ({interaction.user.id}) with query: '{current}'")
        try:
            with open("registered.json", "r") as f:
                data = json.load(f)
            logger.debug("Successfully loaded registered.json for source channel autocomplete")
        except FileNotFoundError:
            logger.warning("registered.json not found for source channel autocomplete")
            return []
        except Exception as e:
            logger.error(f"Error loading registered.json for source channel autocomplete: {e}")
            return []

        channels = [
            entry for entry in data["register"]
            if entry["guild_id"] == str(interaction.guild.id) and entry["registrator_id"] == str(interaction.user.id)
        ]

        results = []
        for entry in channels:
            guild = bot.get_guild(int(entry["guild_id"]))
            channel = guild.get_channel(int(entry["channel_id"])) if guild else None
            if channel:
                name = f"{channel.name} ({entry['channel_id']})"
            else:
                name = f"{entry.get('channel_name', 'Channel')} ({entry['channel_id']})"
            if current.lower() in name.lower():
                results.append(app_commands.Choice(name=name, value=entry["channel_id"]))

        logger.debug(f"Returning {len(results)} source channel autocomplete results")
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

    class RegisterChannelSelect(discord.ui.ChannelSelect):
        def __init__(self, invoker_id: str):
            super().__init__(
                placeholder="Select a channel to register",
                min_values=1,
                max_values=1,
                channel_types=[discord.ChannelType.text, discord.ChannelType.forum],
            )
            self.invoker_id = invoker_id

        async def callback(self, interaction: discord.Interaction):
            if str(interaction.user.id) != self.invoker_id:
                await interaction.response.send_message("This menu isn't for you.", ephemeral=True)
                return

            if not helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "register_channel"):
                await interaction.response.send_message("You have no permission to register channels for message forwarding.", ephemeral=True)
                return

            selected_channel = self.values[0]
            if selected_channel.type not in (discord.ChannelType.text, discord.ChannelType.forum):
                await interaction.response.send_message("This command is available for text or forum channels only", ephemeral=True)
                return

            try:
                registered_channels = helpers.load_registered_channels()
            except Exception as e:
                logger.error(f"Failed to load registered channels: {e}")
                await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
                return

            guild_id = str(interaction.guild.id)
            guild_name = interaction.guild.name if interaction.guild else "Unknown Guild"
            channel_id = str(selected_channel.id)

            for entry in registered_channels["register"]:
                if entry["guild_id"] == guild_id and entry["channel_id"] == channel_id:
                    await interaction.response.send_message("This channel is already registered for message forwarding.", ephemeral=True)
                    return

            entry = {
                "guild_id": guild_id,
                "guild_name": guild_name,
                "channel_id": channel_id,
                "channel_name": selected_channel.name,
                "registrator_id": str(interaction.user.id),
                "registrator_name": interaction.user.display_name,
            }

            registered_channels["register"].append(entry)

            try:
                with open("registered.json", "w") as f:
                    json.dump(registered_channels, f, indent=4, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Failed to save registered channels data: {e}")
                await interaction.response.send_message("An error occurred while saving data.", ephemeral=True)
                return

            self.view.stop()
            await interaction.response.send_message(f"Channel **{selected_channel.name}** registered for message forwarding.", ephemeral=True)

    class RegisterChannelSelectView(discord.ui.View):
        def __init__(self, invoker_id: str):
            super().__init__(timeout=120)
            self.add_item(RegisterChannelSelect(invoker_id))

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True

    @bot.tree.command(name="register_channel", description="Register a channel via dropdown selection")
    async def register_channel(interaction: discord.Interaction):
        logger.info(
            "register_channel invoked by %s (%s) in guild %s (%s)",
            interaction.user.display_name,
            interaction.user.id,
            interaction.guild.name if interaction.guild else "Unknown Guild",
            interaction.guild.id if interaction.guild else "Unknown Guild",
        )

        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        if not helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "register_channel"):
            await interaction.response.send_message("You have no permission to register channels for message forwarding.", ephemeral=True)
            return

        view = RegisterChannelSelectView(str(interaction.user.id))
        await interaction.response.send_message("Select a channel to register:", view=view, ephemeral=True)
        
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

        # Create a readable message with all registered channels
        lines = ["Registered channels for message forwarding:", ""]
        channel_count = 0
        for entry in registered_channels["register"]:
            guild = bot.get_guild(int(entry["guild_id"]))
            channel = guild.get_channel(int(entry["channel_id"])) if guild else None
            guild_name = guild.name if guild else entry.get("guild_name", f"Guild {entry['guild_id']}")
            channel_name = channel.name if channel else entry.get("channel_name", f"Channel {entry['channel_id']}")

            lines.append(f"**Guild:** {guild_name}")
            lines.append(f"**Channel:** {channel_name}")
            if not channel:
                lines.append("`Channel not found`")
            lines.append(f"`Guild ID: {entry['guild_id']} | Channel ID: {entry['channel_id']}`")
            lines.append("")
            channel_count += 1
        
        logger.info(f"Displayed {channel_count} registered channels to {interaction.user.display_name} ({interaction.user.id})")
        await interaction.response.send_message("\n".join(lines).rstrip(), ephemeral=True)


    async def _perform_link_channel(interaction: discord.Interaction, source_channel_id: str, target_guild_id: str, target_channel_id: str, group_name: str):
        group_name = group_name.strip()
        if not group_name:
            await interaction.response.send_message("Group name cannot be empty.", ephemeral=True)
            return

        try:
            registered_channels = commands_helpers.load_registered_channels()
            logger.debug("Successfully loaded registered channels data")
        except Exception as e:
            logger.error(f"Failed to load registered channels: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        if not commands_helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "link_channel"):
            logger.warning(f"User {interaction.user.display_name} ({interaction.user.id}) denied permission to link channel")
            await interaction.response.send_message("You have no permission to link channels for message forwarding.", ephemeral=True)
            return

        if not await commands_helpers.is_channel_registered_by_user_id(registered_channels, str(interaction.guild.id), source_channel_id, str(interaction.user.id)):
            await interaction.response.send_message("You can only link channels that you have registered in this server.", ephemeral=True)
            return

        if not await commands_helpers.is_channel_registered(registered_channels, target_guild_id, target_channel_id):
            logger.warning(f"Target channel {target_channel_id} in guild {target_guild_id} is not registered")
            await interaction.response.send_message("Target channel is not registered for message forwarding.", ephemeral=True)
            return

        if not await commands_helpers.is_channel_registered_by_user_id(registered_channels, target_guild_id, target_channel_id, str(interaction.user.id)):
            logger.warning(f"Target channel {target_channel_id} in guild {target_guild_id} is not registered by user {interaction.user.display_name} ({interaction.user.id})")
            await interaction.response.send_message("You can only link channels that you have registered.", ephemeral=True)
            return

        source_channel = interaction.guild.get_channel(int(source_channel_id)) if interaction.guild else None
        if not source_channel:
            logger.warning(f"Source channel {source_channel_id} not found in guild {interaction.guild.id}")
            await interaction.response.send_message("Source channel not found in this server.", ephemeral=True)
            return

        target_guild = bot.get_guild(int(target_guild_id))
        target_channel = target_guild.get_channel(int(target_channel_id)) if target_guild else None

        current_invite_url = await commands_helpers.create_invite(source_channel)
        target_invite_url = await commands_helpers.create_invite(target_channel)

        try:
            linked_channels = commands_helpers.load_linked_channels()
        except Exception as e:
            logger.error(f"Failed to load linked channels: {e}")
            await interaction.response.send_message("An error occurred while loading linked channels data.", ephemeral=True)
            return

        current_entry = {
            "channel_id": str(source_channel.id),
            "channel_name": str(source_channel.name),
            "guild_id": str(source_channel.guild.id),
            "guild_name": interaction.guild.name if interaction.guild else "Unknown Guild",
            "invite_url": current_invite_url
        }

        target_registered_entry = next(
            (
                entry for entry in registered_channels.get("register", [])
                if entry["guild_id"] == target_guild_id and entry["channel_id"] == target_channel_id
            ),
            None,
        )

        target_entry = {
            "channel_id": target_channel_id,
            "channel_name": target_channel.name if target_channel else (target_registered_entry.get("channel_name") if target_registered_entry else "Unknown Channel"),
            "guild_id": target_guild_id,
            "guild_name": target_guild.name if target_guild else (target_registered_entry.get("guild_name") if target_registered_entry else "Unknown Server"),
            "invite_url": target_invite_url
        }

        if current_entry["guild_id"] == target_entry["guild_id"] and current_entry["channel_id"] == target_entry["channel_id"]:
            logger.warning(f"User {interaction.user.display_name} tried to link channel to itself")
            await interaction.response.send_message("You cannot link a channel to itself.", ephemeral=True)
            return

        if commands_helpers.is_channel_already_linked(current_entry["channel_id"], target_entry["channel_id"], linked_channels):
            logger.warning(f"Channels {current_entry['channel_id']} and {target_entry['channel_id']} are already linked")
            await interaction.response.send_message("This channel is already linked with the target channel.", ephemeral=True)
            return

        if commands_helpers.is_channel_in_any_group(current_entry["channel_id"], linked_channels) or commands_helpers.is_channel_in_any_group(target_entry["channel_id"], linked_channels):
            logger.warning(f"One of the channels ({current_entry['channel_id']} or {target_entry['channel_id']}) is already part of a group")
            await interaction.response.send_message("One of the channels is already part of a group.", ephemeral=True)
            return

        commands_helpers.add_new_linked_group(linked_channels, group_name, current_entry, target_entry)
        try:
            commands_helpers.save_json_file("linked_channels.json", linked_channels)
            logger.info(f"Successfully created new link group '{group_name}' with channels {[current_entry['channel_id'], target_entry['channel_id']]}")
        except Exception as e:
            logger.error(f"Failed to save linked channels data: {e}")
            await interaction.response.send_message("An error occurred while saving link data.", ephemeral=True)
            return

        try:
            commands_helpers.remove_channels_from_registered(registered_channels, [str(source_channel.id), target_channel_id], [str(interaction.guild.id), target_guild_id])
            commands_helpers.save_json_file("registered.json", registered_channels)
            logger.info("Removed linked channels from registered.json")
        except Exception as e:
            logger.error(f"Failed to update registered.json after linking: {e}")

        commands_helpers.remove_registrator(str(interaction.user.id), str(interaction.guild.id))
        logger.debug(f"Removed user {interaction.user.display_name} from temporary registrators")

        await interaction.response.send_message(
            f"Channel **{source_channel.name}** linked with **{target_entry['channel_name']}** in **{target_entry['guild_name']}**.",
            ephemeral=True
        )

    class LinkChannelModal(discord.ui.Modal, title="Link Channels"):
        def __init__(self, source_options: list[discord.SelectOption], target_options: list[discord.SelectOption]):
            super().__init__()
            self.source_channel_select = discord.ui.Select(
                placeholder="Select source channel in this server",
                min_values=1,
                max_values=1,
                options=source_options,
                custom_id="link_channel_source_select",
            )
            self.target_channel_select = discord.ui.Select(
                placeholder="Select target channel on another server",
                min_values=1,
                max_values=1,
                options=target_options,
                custom_id="link_channel_target_select",
            )
            self.group_name_input = discord.ui.TextInput(
                placeholder="Enter linked group name",
                min_length=1,
                max_length=100,
                custom_id="link_channel_group_name",
            )
            self.add_item(
                discord.ui.Label(
                    text="Source channel",
                    component=self.source_channel_select,
                )
            )
            self.add_item(
                discord.ui.Label(
                    text="Target channel",
                    component=self.target_channel_select,
                )
            )
            self.add_item(
                discord.ui.Label(
                    text="Group name",
                    component=self.group_name_input,
                )
            )

        async def on_submit(self, interaction: discord.Interaction):
            source_channel_id = self.source_channel_select.values[0]
            target_value = self.target_channel_select.values[0]
            target_guild_id, target_channel_id = target_value.split(":", 1)
            await _perform_link_channel(
                interaction,
                source_channel_id=source_channel_id,
                target_guild_id=target_guild_id,
                target_channel_id=target_channel_id,
                group_name=str(self.group_name_input.value).strip(),
            )

    @bot.tree.command(name="link_channel", description="Link your registered channel with another registered channel via modal")
    async def link_channel(interaction: discord.Interaction):
        logger.info(
            "link_channel modal invoked by %s (%s) in guild %s (%s)",
            interaction.user.display_name,
            interaction.user.id,
            interaction.guild.name,
            interaction.guild.id,
        )

        try:
            registered_channels = commands_helpers.load_registered_channels()
            logger.debug("Successfully loaded registered channels data")
        except Exception as e:
            logger.error(f"Failed to load registered channels: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        if not commands_helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "link_channel"):
            logger.warning(f"User {interaction.user.display_name} ({interaction.user.id}) denied permission to link channel")
            await interaction.response.send_message("You have no permission to link channels for message forwarding.", ephemeral=True)
            return

        source_entries = [
            entry for entry in registered_channels.get("register", [])
            if entry["guild_id"] == str(interaction.guild.id) and entry["registrator_id"] == str(interaction.user.id)
        ]
        if not source_entries:
            await interaction.response.send_message("You have no registered channels in this server.", ephemeral=True)
            return

        target_entries = [
            entry for entry in registered_channels.get("register", [])
            if entry["guild_id"] != str(interaction.guild.id) and entry["registrator_id"] == str(interaction.user.id)
        ]
        if not target_entries:
            await interaction.response.send_message("You have no registered channels on other servers to link with.", ephemeral=True)
            return

        source_options = []
        for entry in source_entries[:25]:
            guild = bot.get_guild(int(entry["guild_id"]))
            channel = guild.get_channel(int(entry["channel_id"])) if guild else None
            channel_name = channel.name if channel else entry.get("channel_name", entry["channel_id"])
            guild_name = format_guild_display_name(guild, entry.get("guild_name", interaction.guild.name))
            source_options.append(
                discord.SelectOption(
                    label=channel_name[:100],
                    value=entry["channel_id"],
                    description=guild_name[:100],
                )
            )

        target_options = []
        for entry in target_entries[:25]:
            guild = bot.get_guild(int(entry["guild_id"]))
            channel = guild.get_channel(int(entry["channel_id"])) if guild else None
            channel_name = channel.name if channel else entry.get("channel_name", entry["channel_id"])
            guild_name = format_guild_display_name(guild, entry.get("guild_name", entry["guild_id"]))
            target_options.append(
                discord.SelectOption(
                    label=channel_name[:100],
                    value=f"{entry['guild_id']}:{entry['channel_id']}",
                    description=guild_name[:100],
                )
            )

        modal = LinkChannelModal(source_options=source_options, target_options=target_options)
        await interaction.response.send_modal(modal)

    @bot.tree.command(name="show_linked_channels", description="Show linked servers and channels with this channel")
    async def linked_channels(interaction: discord.Interaction):
        '''Show all linked channels for the current server'''
        logger.info(f"show_linked_channels command invoked by {interaction.user.display_name} ({interaction.user.id}) in guild {interaction.guild.name} ({interaction.guild.id}), channel {interaction.channel.name} ({interaction.channel.id})")
        
        try:
            linked_channels = helpers.load_linked_channels()
        except Exception as e:
            logger.error(f"Failed to load linked channels: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        current_guild_id = str(interaction.guild.id)
        guild_groups = []

        for group in linked_channels["groups"]:
            local_links = [link for link in group["links"] if link["guild_id"] == current_guild_id]
            if local_links:
                guild_groups.append((group, local_links))

        if not guild_groups:
            logger.debug(f"Guild {interaction.guild.name} ({current_guild_id}) has no linked channels")
            await interaction.response.send_message("There are no linked channels for this server.", ephemeral=True)
            return

        lines = []

        for group, local_links in guild_groups:
            if lines:
                lines.append("")
            lines.append(f"## Group *{group['group_name']}*:")

            for local_link in local_links:
                local_guild = bot.get_guild(int(local_link["guild_id"]))
                local_channel = local_guild.get_channel(int(local_link["channel_id"])) if local_guild else None
                local_channel_name = local_channel.name if local_channel else local_link.get("channel_name", local_link["channel_id"])
                local_guild_name = local_guild.name if local_guild else local_link.get("guild_name", local_link["guild_id"])
                lines.append(f":pushpin: `{local_channel_name}` - **{local_guild_name}**")

                for linked_link in group["links"]:
                    if linked_link["channel_id"] == local_link["channel_id"] and linked_link["guild_id"] == local_link["guild_id"]:
                        continue

                    linked_guild = bot.get_guild(int(linked_link["guild_id"]))
                    linked_channel = linked_guild.get_channel(int(linked_link["channel_id"])) if linked_guild else None
                    linked_channel_name = linked_channel.name if linked_channel else linked_link.get("channel_name", linked_link["channel_id"])
                    linked_guild_name = linked_guild.name if linked_guild else linked_link.get("guild_name", linked_link["guild_id"])
                    lines.append(f"- `{linked_channel_name}` - **{linked_guild_name}**")

        msg = "\n".join(lines)
        await interaction.response.send_message(msg, ephemeral=True)

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

    async def _perform_link_channel_to_group(interaction: discord.Interaction, source_channel_id: str, group_name: str):
        logger.info(
            "link_channel_to_group perform invoked by %s (%s) in guild %s (%s), source channel: %s, group: %s",
            interaction.user.display_name,
            interaction.user.id,
            interaction.guild.name,
            interaction.guild.id,
            source_channel_id,
            group_name,
        )

        if not commands_helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "link_channel"):
            logger.warning(f"User {interaction.user.display_name} ({interaction.user.id}) denied permission to link channel to group")
            await interaction.response.send_message("You have no permission to link channels to groups", ephemeral=True)
            return

        try:
            registered_data = commands_helpers.load_registered_channels()
            logger.debug("Successfully loaded registered channels data")
        except Exception as e:
            logger.error(f"Failed to load registered channels: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        try:
            linked_channels = commands_helpers.load_linked_channels()
        except Exception as e:
            logger.error(f"Failed to load linked channels: {e}")
            await interaction.response.send_message("An error occurred while loading linked channels data.", ephemeral=True)
            return

        if not await commands_helpers.is_channel_registered(registered_data, str(interaction.guild.id), source_channel_id):
            logger.warning(f"Channel {source_channel_id} is not registered")
            await interaction.response.send_message("This channel is not registered for message forwarding.", ephemeral=True)
            return

        if not await commands_helpers.is_channel_registered_by_user_id(registered_data, str(interaction.guild.id), source_channel_id, str(interaction.user.id)):
            logger.warning(f"Channel {source_channel_id} is not registered by user {interaction.user.display_name} ({interaction.user.id})")
            await interaction.response.send_message("You can only link channels that you have registered.", ephemeral=True)
            return

        if commands_helpers.is_channel_in_any_group(str(source_channel_id), linked_channels):
            logger.warning(f"Channel {source_channel_id} is already linked to another group.")
            await interaction.response.send_message("This channel is already linked to another group.", ephemeral=True)
            return

        group = commands_helpers.get_group_by_name(linked_channels, group_name)
        if not group:
            logger.warning(f"No group found with name '{group_name}'")
            await interaction.response.send_message(f"No group found with name **{group_name}**.", ephemeral=True)
            return

        not_all_registered, not_registered_link = await commands_helpers.are_all_group_channels_registered_by_user(group, registered_data, str(interaction.user.id))
        if not_all_registered:
            logger.warning(f"Channel {not_registered_link['channel_name']} from {not_registered_link['guild_name']} in group {group_name} is not registered by user {interaction.user.display_name}")
            await interaction.response.send_message(
                f"Channel **{not_registered_link['channel_name']}** from server **{not_registered_link['guild_name']}** in group **{group_name}** is not registered or registered by another user.",
                ephemeral=True
            )
            return

        source_channel = interaction.guild.get_channel(int(source_channel_id)) if interaction.guild else None
        if not source_channel:
            await interaction.response.send_message("Source channel not found in this server.", ephemeral=True)
            return

        try:
            invite_url = await commands_helpers.create_invite(source_channel)
            logger.debug(f"Generated invite link for channel {source_channel.name} ({source_channel.id})")
        except Exception as e:
            logger.error(f"Failed to generate invite link for channel {source_channel.name} ({source_channel.id}): {e}")
            invite_url = None

        current_entry = {
            "channel_id": str(source_channel.id),
            "channel_name": source_channel.name,
            "guild_id": str(interaction.guild.id),
            "guild_name": interaction.guild.name if interaction.guild else "Unknown Guild",
            "invite_url": invite_url
        }

        group["links"].append(current_entry)
        group["channel_list"].append(current_entry["channel_id"])

        try:
            commands_helpers.save_json_file("linked_channels.json", linked_channels)
            logger.info(f"Successfully linked channel {source_channel.name} ({source_channel.id}) to group '{group_name}'")
        except Exception as e:
            logger.error(f"Failed to save linked channels data: {e}")
            await interaction.response.send_message("An error occurred while saving data.", ephemeral=True)
            return

        commands_helpers.remove_registrator(str(interaction.user.id), str(interaction.guild.id))
        logger.debug(f"Removed user {interaction.user.display_name} from temporary registrators")

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
            f"Channel **{source_channel.name}** has been linked to the group **{group_name}**.",
            ephemeral=True
        )

    class LinkToGroupSourceSelect(discord.ui.Select):
        def __init__(self, source_options: list[discord.SelectOption], selected_source_channel_id: str | None = None):
            options = [
                discord.SelectOption(
                    label=option.label,
                    value=option.value,
                    description=option.description,
                    emoji=option.emoji,
                    default=option.value == selected_source_channel_id,
                )
                for option in source_options
            ]
            super().__init__(
                placeholder="Select a channel to link",
                min_values=1,
                max_values=1,
                options=options,
            )

        async def callback(self, interaction: discord.Interaction):
            self.view.selected_source_channel_id = self.values[0]
            self.view.refresh_components()
            await interaction.response.edit_message(content=self.view.render_message(), view=self.view)

    class LinkToGroupNameSelect(discord.ui.Select):
        def __init__(self, group_options: list[discord.SelectOption], selected_group_name: str | None = None):
            options = [
                discord.SelectOption(
                    label=option.label,
                    value=option.value,
                    description=option.description,
                    emoji=option.emoji,
                    default=option.value == selected_group_name,
                )
                for option in group_options
            ]
            super().__init__(
                placeholder="Select a group",
                min_values=1,
                max_values=1,
                options=options,
            )

        async def callback(self, interaction: discord.Interaction):
            self.view.selected_group_name = self.values[0]
            self.view.refresh_components()
            await interaction.response.edit_message(content=self.view.render_message(), view=self.view)

    class LinkChannelToGroupView(discord.ui.View):
        def __init__(self, invoker_id: str, source_options: list[discord.SelectOption], group_options: list[discord.SelectOption]):
            super().__init__(timeout=120)
            self.invoker_id = invoker_id
            self.source_options = source_options
            self.group_options = group_options
            self.selected_source_channel_id: str | None = None
            self.selected_group_name: str | None = None
            self.source_select = LinkToGroupSourceSelect(source_options)
            self.group_select = LinkToGroupNameSelect(group_options)
            self.add_item(self.source_select)
            self.add_item(self.group_select)
            self.refresh_components()

        def get_selected_source_label(self) -> str | None:
            for option in self.source_options:
                if option.value == self.selected_source_channel_id:
                    return option.label
            return None

        def get_selected_group_label(self) -> str | None:
            for option in self.group_options:
                if option.value == self.selected_group_name:
                    return option.label
            return None

        def render_message(self) -> str:
            lines = ["Select a channel and a group to link:"]
            if self.selected_source_channel_id:
                lines.append(f"**Channel:** {self.get_selected_source_label()}")
            if self.selected_group_name:
                lines.append(f"**Group:** {self.get_selected_group_label()}")
            return "\n".join(lines)

        def refresh_components(self) -> None:
            selected_channel_label = self.get_selected_source_label()
            selected_group_label = self.get_selected_group_label()

            self.source_select.placeholder = (
                f"Channel: {selected_channel_label}"[:150]
                if selected_channel_label else
                "Select a channel to link"
            )
            self.group_select.placeholder = (
                f"Group: {selected_group_label}"[:150]
                if selected_group_label else
                "Select a group"
            )

            for option in self.source_select.options:
                option.default = option.value == self.selected_source_channel_id

            for option in self.group_select.options:
                option.default = option.value == self.selected_group_name

            self.confirm.disabled = not (self.selected_source_channel_id and self.selected_group_name)

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if str(interaction.user.id) != self.invoker_id:
                await interaction.response.send_message("This menu isn't for you.", ephemeral=True)
                return False
            return True

        @discord.ui.button(label="Link to group", style=discord.ButtonStyle.primary)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            if not self.selected_source_channel_id or not self.selected_group_name:
                await interaction.response.send_message("Select both a source channel and a group first.", ephemeral=True)
                return
            self.stop()
            await _perform_link_channel_to_group(
                interaction,
                source_channel_id=self.selected_source_channel_id,
                group_name=self.selected_group_name,
            )

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True

    @bot.tree.command(name="link_channel_to_group", description="Link one of your registered channels to an existing group")
    async def link_channel_to_group(interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        logger.info(f"link_channel_to_group command invoked by {interaction.user.display_name} ({interaction.user.id}) in guild {interaction.guild.name} ({interaction.guild.id}), channel {interaction.channel.name} ({interaction.channel.id})")

        if not commands_helpers.has_user_permission(str(interaction.user.id), str(interaction.guild.id), "link_channel"):
            logger.warning(f"User {interaction.user.display_name} ({interaction.user.id}) denied permission to link channel to group")
            await interaction.response.send_message("You have no permission to link channels to groups", ephemeral=True)
            return

        try:
            registered_data = commands_helpers.load_registered_channels()
            logger.debug("Successfully loaded registered channels data")
        except Exception as e:
            logger.error(f"Failed to load registered channels: {e}")
            await interaction.response.send_message("An error occurred while loading data.", ephemeral=True)
            return

        try:
            linked_channels = commands_helpers.load_linked_channels()
            logger.debug("Successfully loaded linked channels data")
        except Exception as e:
            logger.error(f"Failed to load linked channels: {e}")
            await interaction.response.send_message("An error occurred while loading linked channels data.", ephemeral=True)
            return

        source_entries = []
        for entry in registered_data.get("register", []):
            if entry["guild_id"] != str(interaction.guild.id) or entry["registrator_id"] != str(interaction.user.id):
                continue
            if commands_helpers.is_channel_in_any_group(entry["channel_id"], linked_channels):
                continue
            source_entries.append(entry)

        if not source_entries:
            await interaction.response.send_message("You have no registered channels in this server available for linking.", ephemeral=True)
            return

        group_options = []
        for group in linked_channels.get("groups", []):
            not_all_registered, _ = await commands_helpers.are_all_group_channels_registered_by_user(group, registered_data, str(interaction.user.id))
            if not not_all_registered:
                group_options.append(
                    discord.SelectOption(
                        label=group["group_name"][:100],
                        value=group["group_name"],
                        description=f"{len(group.get('links', []))} linked channel(s)"[:100],
                    )
                )

        if not group_options:
            await interaction.response.send_message("You have no existing groups available for linking.", ephemeral=True)
            return

        source_options = []
        for entry in source_entries[:25]:
            guild = bot.get_guild(int(entry["guild_id"]))
            channel = guild.get_channel(int(entry["channel_id"])) if guild else None
            channel_name = channel.name if channel else entry.get("channel_name", entry["channel_id"])
            guild_name = format_guild_display_name(guild, entry.get("guild_name", interaction.guild.name))
            source_options.append(
                discord.SelectOption(
                    label=channel_name[:100],
                    value=entry["channel_id"],
                    description=guild_name[:100],
                )
            )

        view = LinkChannelToGroupView(str(interaction.user.id), source_options, group_options[:25])
        await interaction.response.send_message(view.render_message(), view=view, ephemeral=True)

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

        lines = [f"Invite links for linked channels in group **{found_group['group_name']}**:"]
        for link in found_group.get("links", []):
            invite_url = link.get("invite_url")
            if invite_url:
                lines.append(f"→ [{link.get('guild_name')}]({invite_url}) | #**{link.get('channel_name')}**")
            else:
                lines.append(f"→ [{link.get('guild_name')}] | #**{link.get('channel_name')}** (No invite found)")

        msg = "\n".join(lines)

        await interaction.response.send_message(msg)

        broadcast_targets = [link for link in found_group.get("links", []) if link.get("channel_id") != current_channel_id]
        forwarded_channels = []
        for target in broadcast_targets:
            channel_id = target.get("channel_id")
            try:
                target_channel = bot.get_channel(int(channel_id)) if channel_id else None
            except Exception as e:
                logger.error(f"Failed to resolve broadcast channel ID {channel_id}: {e}")
                continue

            if not target_channel:
                logger.warning(f"Linked channel with ID {channel_id} not found in bot cache for broadcast")
                continue

            try:
                await target_channel.send(msg)
                forwarded_channels.append(f"{target_channel.guild.name}#{target_channel.name}")
            except Exception as e:
                logger.error(f"Failed to send invites message to {target_channel.guild.name}#{target_channel.name}: {e}")

        if forwarded_channels:
            logger.info(f"Broadcasted invite list to linked channels: {', '.join(forwarded_channels)}")

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
            await interaction.response.send_message(
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
