# HackBridge Bot Commands

This document describes all bot slash commands based on the actual logic in `commands.py`, `helpers.py`, `commands_helpers.py`, and `roles.py`.

## Roles and Permissions

### Roles

- `SuperAdmin`
- `Admin`
- `Registrator`

### Permission Matrix

| Command / permission | SuperAdmin | Admin | Registrator |
| --- | --- | --- | --- |
| `/register_channel` | yes | yes | yes |
| `/link_channel` | yes | yes | yes |
| `/link_channel_to_group` | yes | yes | yes |
| `/unlink_channel` | yes | yes | no |
| `/remove_channel_registration` | yes | yes | no |
| `/set_admin` | yes | no | no |
| `/set_registrator` | yes | yes | no |
| `/remove_admin` | yes | no | no |
| `/remove_registrator` | yes | yes | no |
| `/show_registered_channels` | yes, sees all | yes, sees all | yes, but only own entries |
| `/show_linked_channels` | no role check | no role check | no role check |
| `/show_admins` | no role check | no role check | no role check |
| `/set_superadmin` | separate logic | separate logic | separate logic |
| `/set_my_avatar` | no role check | no role check | no role check |
| `/remove_my_avatar` | no role check | no role check | no role check |
| `/show_my_avatar` | no role check | no role check | no role check |
| `/get_invites` | no role check | no role check | no role check |
| `/update_invites` | no role check | no role check | no role check |

### Special Restrictions

- A `SuperAdmin` cannot be assigned as `Admin` through `/set_admin`.
- A `SuperAdmin` or `Admin` cannot be assigned as `Registrator` through `/set_registrator`.
- In the current implementation, `Registrator` is effectively one-time use: after a successful `link_channel` or `link_channel_to_group`, the registrator entry is removed.
- Most commands are designed for server use. Some commands check this explicitly, while others simply assume `interaction.guild` and `interaction.channel` exist.

## General Flow

### Registered channels

`/register_channel` adds a channel to `registered_channels`. At this stage the channel is only registered and is not yet linked to anything.

### Linked channels

`/link_channel` creates a new linked group from two previously registered channels.

`/link_channel_to_group` adds another registered channel to an existing linked group.

After successful linking, the relevant channels are removed from the registered channels state and moved into linked groups.

## Commands

## `/register_channel`

### Who can use it

- `SuperAdmin`
- `Admin`
- `Registrator`

### Conditions

- The command only works inside a server.
- The dropdown only allows `text` and `forum` channels.
- The same channel cannot be registered twice.

### What it does

- Shows an ephemeral dropdown with channels from the current server.
- After selection it saves:
  - `guild_id`
  - `guild_name`
  - `channel_id`
  - `channel_name`
  - `registrator_id`
  - `registrator_name`

### Result

- The channel becomes available for later linking.

## `/show_registered_channels`

### Who can use it

- Any user, but the visible scope depends on role.

### Conditions

- If the caller is a `SuperAdmin` or `Admin`, they see all registered channels in the state.
- If the caller does not have one of those roles, they only see channels registered by themselves.

### What it does

- Shows the list of registered channels.
- For each entry it displays:
  - `Guild`
  - `Channel`
  - `Guild ID` and `Channel ID`
- If the channel is missing from the current Discord cache, it shows `Channel not found`.

### Response format

- Ephemeral response.

## `/link_channel`

### Who can use it

- `SuperAdmin`
- `Admin`
- `Registrator`

### Conditions

- The command is used in a server.
- The user must have at least one registered channel in the current server.
- The user must have at least one registered channel in another server.
- Both channels must be registered by the same user who runs the command.
- A channel cannot be linked to itself.
- Channels that are already linked together cannot be linked again.
- A channel that already belongs to any group cannot be used.
- `group_name` cannot be empty.

### What it does

- Opens a modal with:
  - source channel selection from the current server
  - target channel selection from another server
  - `group_name` input
- Creates invites for the source and target channels.
- Creates a new linked group containing the two channels.
- Removes both channels from the registered list.
- Removes the calling user from `registrators` for the current guild.

### Important detail

- The target channel must not just be registered by someone, it must be registered by the same user who invokes the command.

### Response format

- Ephemeral response.

## `/show_linked_channels`

### Who can use it

- Any user.

### Conditions

- There is no role check.
- The command only shows groups that include at least one channel from the current guild.

### What it does

- Finds all linked groups that include the current server.
- For each group it shows:
  - the group name
  - local channels from the current server
  - the other linked channels in that group

### Response format

- Ephemeral response.

## `/unlink_channel`

### Who can use it

- `SuperAdmin`
- `Admin`

### Conditions

- The command operates on the current channel where it is called.
- The current channel must belong to a linked group.

### What it does

- Removes the current channel from the matching group.
- Deletes it from both `links` and `channel_list`.
- If only one channel remains in the group afterwards, the whole group is deleted.

### Response format

- Ephemeral response.

## `/remove_channel_registration`

### Who can use it

- `SuperAdmin`
- `Admin`

### Conditions

- The command operates on the current channel.
- The current channel must exist in the registered channels list.

### What it does

- Removes the current channel from the registered channels state.

### Response format

- Ephemeral response.

## `/set_admin`

### Who can use it

- `SuperAdmin` only.

### Conditions

- You cannot assign `Admin` to a user who is already treated as `can't_be_admin`.
- In the current logic this means you cannot assign `Admin` to a user who is already `SuperAdmin` in this guild.
- The target user must not already be an `Admin` in this guild.

### What it does

- Adds the target user to the `admins` list for the current guild.

### Response format

- Ephemeral response.

## `/set_superadmin`

### Who can use it

- Any server user with the Discord `administrator` permission.

### Conditions

- This command uses separate logic and does not depend on the bot's internal role system.
- Only one `SuperAdmin` can exist per server.
- The calling user must not already be `SuperAdmin` in this guild.

### What it does

- Assigns the calling user as `SuperAdmin` for the current guild.

### Response format

- Ephemeral response.

## `/show_admins`

### Who can use it

- Any user.

### Conditions

- There is no role check.

### What it does

- Shows all `Admin` users for the current guild.
- `SuperAdmin` users are not included here, only the `admins` list.

### Response format

- Ephemeral response.

## `/set_registrator`

### Who can use it

- `SuperAdmin`
- `Admin`

### Conditions

- You cannot assign `Registrator` to a user who matches `can't_be_registrator`.
- In the current logic this means you cannot assign `Registrator` to a `SuperAdmin` or `Admin` of the same guild.
- The target user must not already be a registrator in this guild.

### What it does

- Adds the target user to the `registrators` list.
- The command text calls this a `one-time registrator`, which matches the current post-link behavior.

### Response format

- Ephemeral response.

## `/remove_admin`

### Who can use it

- `SuperAdmin` only.

### Conditions

- The target user is selected by `user_id` with autocomplete.
- The target user must exist in the current guild.
- The target user must actually be an `Admin` in this guild.

### What it does

- Removes the target user from the `admins` list for the current guild.

### Response format

- Ephemeral response.

## `/remove_registrator`

### Who can use it

- `SuperAdmin`
- `Admin`

### Conditions

- The target user is selected by `user_id` with autocomplete.
- The target user must exist in the current guild.
- The target user must actually be a `Registrator` in this guild.

### What it does

- Removes the target user from the `registrators` list for the current guild.

### Response format

- Ephemeral response.

## `/link_channel_to_group`

### Who can use it

- `SuperAdmin`
- `Admin`
- `Registrator`

### Conditions

- The command only works inside a server.
- The user must have at least one registered channel in the current server that does not already belong to any group.
- The user must have access to at least one existing group.
- Access to a group is granted only if all channels in that group are already registered by the same user.
- The selected source channel must be registered by the same user.
- The selected source channel must not already belong to another group.

### What it does

- Shows an ephemeral view with two dropdowns:
  - channel selection
  - existing group selection
- After confirmation it:
  - adds the channel to `links`
  - adds its `channel_id` to `channel_list`
  - removes the calling user from `registrators` for the current guild
  - removes all channels of that group from the registered channels state

### Important detail

- This command is intentionally strict: a user can add a channel to an existing group only if the whole group is already fully owned by that same registrator from the registration-state perspective.

### Response format

- Ephemeral response.

## `/set_my_avatar`

### Who can use it

- Any user.

### Conditions

- The `emoji` parameter must contain exactly one emoji.
- Supported formats:
  - one Unicode emoji
  - one Discord custom emoji in the form `<:name:id>` or `<a:name:id>`

### What it does

- Stores the user's emoji avatar in MongoDB.
- That emoji is then used in bridged message headers instead of the default one.

### Response format

- Ephemeral response.

## `/remove_my_avatar`

### Who can use it

- Any user.

### Conditions

- The user must already have a custom avatar set.

### What it does

- Removes the custom emoji avatar for the user.
- After that the bot falls back to the default emoji avatar.

### Response format

- Ephemeral response.

## `/show_my_avatar`

### Who can use it

- Any user.

### What it does

- Shows the user's current custom avatar.
- If no custom avatar is set, it reports that the default emoji is being used.

### Response format

- Ephemeral response.

## `/get_invites`

### Who can use it

- Any user.

### Conditions

- The current channel must belong to a linked group.

### What it does

- Finds the linked group for the current channel.
- Builds a list of invite links for all channels in that group.
- Sends that message in the current channel.
- Then tries to broadcast the same message to every other channel in the group.

### Important detail

- This is not an ephemeral response.
- The command broadcasts to linked channels if the bot can resolve them and send messages there.

## `/update_invites`

### Who can use it

- Any user.

### Conditions

- The current channel must belong to a linked group.

### What it does

- Tries to regenerate an invite for every channel in the group.
- If invite creation succeeds, it updates `invite_url` in the linked group state.
- If a channel is unavailable or invite creation fails, that is included in the report.

### Current implementation detail

- If there are guilds where invite creation fails, the command first sends an ephemeral message listing the failed guilds.
- After that it still tries to call `interaction.response.send_message(...)` again for the final report.
- That conflicts with the Discord interaction lifecycle and can produce a second-response error if `failed_guilds` is not empty.

### Response format

- In the normal success path, the response is ephemeral.

## Notes About the Current Implementation

- `/show_admins`, `/show_linked_channels`, `/get_invites`, `/update_invites`, `/set_my_avatar`, `/remove_my_avatar`, and `/show_my_avatar` are not restricted by the bot's internal role system.
- `/show_admins` only displays `admins`, not `superadmins`.
- `/get_invites` and `/update_invites` do not perform separate permission checks.
- `/link_channel` and `/link_channel_to_group` remove the caller's registrator role after successful completion.
- In practice, `Registrator` is only needed for channel registration and linking operations.
