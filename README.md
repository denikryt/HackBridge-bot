# 🌉 HackBridge Bot

A powerful Discord bot that creates seamless message bridges between multiple Discord servers and channels, enabling cross-server communication with advanced permission management and message tracking.

Originally created for the Kyiv Hackerspace Discord community to facilitate communication across multiple servers and channels 

## ⚠️ Important Disclaimers

- **⚠️ Development Status**: This project is currently under active development. Features may change and bugs may occur.
- **🚫 Multiple Instances**: Running two instances of this bot on the same server may cause conflicts. Only one instance per server is recommended.
- **🔒 Data Privacy**: Only message IDs are stored in the database for tracking purposes. Message content is never stored server-side.
- **📊 Database Storage**: The bot only stores message relationship data (IDs, channel mappings) - no actual message content is persisted.

## ✨ Features

### 🔗 Channel Linking & Message Forwarding
- **Multi-Server Communication**: Link channels across different Discord servers
- **Group Management**: Create and manage groups of linked channels
- **Real-time Forwarding**: Messages are instantly forwarded to all linked channels
- **Reply Support**: Handles message replies and maintains conversation context
- **Rich Content Support**: Forwards text, images, attachments, and embeds

### 👑 Advanced Permission System
- **SuperAdmin**: Full bot control with server administrator privileges
- **Admin**: Manage registrators and channel operations within their server
- **Registrator**: Temporary role for channel registration and linking
- **Granular Permissions**: Fine-grained control over bot operations

### 📊 Message Tracking & Database
- **MongoDB Integration**: Persistent storage of message relationships
- **Message Grouping**: Track related messages across linked channels
- **Reply Tracking**: Maintain message thread integrity across servers

### 🎨 Customizable Appearance
- **Random Avatar Emojis**: Fun, randomized emoji avatars for forwarded messages
- **Guild Identification**: Clear headers showing message origin

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Discord Bot Token
- MongoDB database (optional but recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/HackBridge-bot.git
   cd HackBridge-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   token=YOUR_DISCORD_BOT_TOKEN
   mongodb_uri=YOUR_MONGODB_CONNECTION_STRING
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

## 📋 Commands Reference

### 🔧 Channel Management

| Command | Description | Permissions |
|---------|-------------|-------------|
| `/register_channel` | Register current channel for message forwarding | Registrator+ |
| `/show_registered_channels` | Display all registered channels | Any user |
| `/remove_channel_registration` | Remove current channel from registration | Registrator+ |

### 🔗 Channel Linking

| Command | Description | Permissions |
|---------|-------------|-------------|
| `/link_channel <guild_id> <channel_id> <group_name>` | Link current channel with another server's channel | Registrator+ |
| `/link_channel_to_group <group_name>` | Add current channel to existing group | Registrator+ |
| `/show_linked_channels` | Show channels linked to current channel | Any user |
| `/unlink_channel` | Remove current channel from its group | Registrator+ |

### 👥 User Management

| Command | Description | Permissions |
|---------|-------------|-------------|
| `/set_superadmin` | Set yourself as superadmin (server admin only) | Server Admin |
| `/set_admin <user>` | Grant admin permissions to a user | SuperAdmin |
| `/set_registrator <user>` | Grant temporary registrator permissions | Admin+ |
| `/show_admins` | Display all bot admins in current server | Any user |
| `/remove_admin <user_id>` | Remove admin permissions | SuperAdmin |
| `/remove_registrator <user_id>` | Remove registrator permissions | Admin+ |

## 🏗️ Architecture

### File Structure
```
HackBridge-bot/
├── main.py                 # Bot entry point and event handlers
├── commands.py             # Slash command implementations
├── messages.py             # Message forwarding logic
├── helpers.py              # Utility functions
├── roles.py                # Permission system classes
├── database.py             # MongoDB operations
├── config.py               # Configuration and constants
├── logger_config.py        # Logging configuration
├── requirements.txt        # Python dependencies
├── avatar.png              # Bot avatar image
├── roles.json              # User roles storage
├── registered.json         # Channel registration data
├── linked_channels.json    # Channel linking configuration
└── logs/                   # Application logs
    └── bot.log
```

### Permission Hierarchy
```
SuperAdmin (Server Administrator)
    ├── Full bot control
    ├── Can set/remove admins
    ├── Cannot be set as admin/registrator
    └── All admin permissions

Admin (Set by SuperAdmin)
    ├── Manage registrators
    ├── Channel operations
    ├── Cannot be set as registrator
    └── All registrator permissions

Registrator (Temporary, set by Admin+)
    ├── Register channels
    ├── Link/unlink channels
    └── Limited to own registered channels
```

## 🔧 Configuration

### Environment Variables
- `token`: Your Discord bot token
- `mongodb_uri`: MongoDB connection string (optional)

### Config Options (`config.py`)
- `AVATAR_EMOJIS`: List of emoji options for message avatars
- `DB_NAME`: MongoDB database name

## 🗃️ Data Storage

### JSON Files
- **`roles.json`**: Stores user permissions and roles
- **`registered.json`**: Tracks registered channels
- **`linked_channels.json`**: Manages channel group configurations

### MongoDB Collections
- Dynamic collections created per channel group
- Stores only message IDs and relationships for reply tracking
- Enables cross-server message threading without storing content
- **No message content is stored** - only metadata for linking purposes

## 🔐 Security Features

- **Permission-based access control**
- **User action logging**
- **Server isolation** (admins only manage their own servers)
- **Temporary registrator system** (automatically removed after linking)
- **Channel ownership validation**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter any issues or have questions:

1. Check the bot logs in `logs/bot.log`
2. Verify your permissions in the server
3. Ensure all required channels are properly registered
4. Open an issue on GitHub with detailed information

## 🔮 Roadmap

- [ ] Web dashboard for easier management
- [ ] Message encryption for sensitive communications
- [ ] Custom message formatting options
- [ ] Message scheduling and delayed forwarding
- [ ] Advanced filtering and moderation features
- [ ] API for external integrations

---

Made with ❤️ for seamless Discord server communication
