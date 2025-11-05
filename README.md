# HackBridge Bot

Originally created for the Kyiv Hackerspace community Discord server and friends around the net.

Discord bridge bot for linking channels (and threads) across servers while keeping strict role-based access control.

## Core Features
- Sync channel and thread messages: send, reply, edit, delete, forward, and mirror reaction adds/removals.
- Custom emoji avatars per user via `/set_my_avatar`.
- SuperAdmin/Admin/Registrator role system with command-level permissions.
- Message privacy: only message IDs are stored in MongoDB; content never leaves Discord.
- Local JSON files keep channel links and server role assignments.

## Usage Flow
1. Install the bot on every server that should participate.
2. Set a SuperAdmin on each server (`/set_superadmin` from a Discord server admin).
3. Grant Admin and/or Registrator roles where needed using `/set_admin` and `/set_registrator`.
4. Register each channel that should be linked with `/register_channel`.
5. Ensure the same user registers every channel within a link group.
6. Link the channels together via `/link_channel`.
7. Optionally attach channels to an existing group with `/link_channel_to_group`.
8. Any group can hold an unlimited number of linked channels.
9. Registrator access is temporary and expires after performing a single channel link.

Commands are exposed via Discord slash commands, each gated by the required role.
Slash-command autocompletions guide the linking process and help fill in the necessary IDs.

## Local Setup
- Requirements: Python 3.8+, running MongoDB instance.
- Create `.env` with `token`, `mongodb_uri`, and `avatar_collection_name`.
- Install deps with `pip install -r requirements.txt` and start the bot using `python main.py`.
