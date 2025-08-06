# 🌉 HackBridge Bot

A Discord bot that creates seamless message bridges between multiple servers and channels, enabling cross-server communication with advanced permission management.

Originally created for the Kyiv Hackerspace Discord community.

## ⚠️ Important Notes

- **Development Status**: Currently under active development
- **Single Instance**: Only run one instance per server to avoid conflicts
- **Privacy**: Only message IDs are stored - no message content is persisted

## ✨ Features

### 🔗 Channel Linking & Message Forwarding
- **Multi-Server Communication**: Link channels across different Discord servers
- **Real-time Forwarding**: Messages are instantly forwarded to all linked channels
- **Reply & Thread Support**: Maintains conversation flow and reply relationships across servers
- **Rich Content Support**: Forwards text, images, attachments, and embeds
- **Message Synchronization**: Edit and delete tracking across all linked channels

### � Smart Message Headers
- **User & Guild Links**: Clickable links to the original user and server in message headers
- **Custom Avatars**: Set personalized avatars using `/set_my_avatar` command
- **Guild Identification**: Clear display of message origin server

### � Permission System
- **SuperAdmin**: Full bot control (server administrators only)
- **Admin**: Manage users and channels within their server
- **Registrator**: Temporary role for channel registration and linking

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Discord Bot Token
- MongoDB (optional but recommended)

### Installation

1. Clone and install:
   ```bash
   git clone https://github.com/yourusername/HackBridge-bot.git
   cd HackBridge-bot
   pip install -r requirements.txt
   ```

2. Create `.env` file:
   ```env
   token=YOUR_DISCORD_BOT_TOKEN
   mongodb_uri=YOUR_MONGODB_CONNECTION_STRING
   ```

3. Run:
   ```bash
   python main.py
   ```

## 📋 Commands

### Channel Management
| Command | Description | Permissions |
|---------|-------------|-------------|
| `/register_channel` | Register current channel for forwarding | Registrator+ |
| `/remove_channel_registration` | Remove channel from registration | Registrator+ |
| `/show_registered_channels` | Display all registered channels | Any user |

### Channel Linking
| Command | Description | Permissions |
|---------|-------------|-------------|
| `/link_channel <guild_id> <channel_id> <group_name>` | Link channel with another server | Registrator+ |
| `/link_channel_to_group <group_name>` | Add channel to existing group | Registrator+ |
| `/show_linked_channels` | Show linked channels | Any user |
| `/unlink_channel` | Remove channel from group | Registrator+ |

### User Management
| Command | Description | Permissions |
|---------|-------------|-------------|
| `/set_superadmin` | Set yourself as superadmin | Server Admin |
| `/set_admin <user>` | Grant admin permissions | SuperAdmin |
| `/set_registrator <user>` | Grant registrator permissions | Admin+ |
| `/show_admins` | Display all bot admins | Any user |
| `/remove_admin <user_id>` | Remove admin permissions | SuperAdmin |
| `/remove_registrator <user_id>` | Remove registrator permissions | Admin+ |

## 📖 Step-by-Step Guide: Linking Channels Between Servers

### 🚀 Quick Setup Instructions

#### 1. **Install the Bot on Both Servers**
   - **Invite HackBridge bot** to both Discord servers where you want to link channels:
     - **[Click here to invite the bot](https://discord.com/oauth2/authorize?client_id=1393520394136457306&permissions=397821471744&integration_type=0&scope=bot)**
   - The bot will automatically get the required permissions (Send Messages, Manage Messages, etc.)

#### 2. **Set Up SuperAdmin (Server Admin Only)**
   - In any public channel on your server, run: `/set_superadmin`
   - ⚠️ **Only Discord server administrators can use this command**
   - This gives you full control over the bot in your server

#### 3. **Grant Permissions to Users from Other Servers**
   - **Option A - Make them Admin**: `/set_admin <user>` (SuperAdmin only)
   - **Option B - Make them Registrator**: `/set_registrator <user>` (Admin+ only)
   - This allows users from other servers to register and link channels

#### 4. **Get Permissions on the Other Server**
   - Ask the SuperAdmin or Admin from the other server to give you permissions:
     - They should run `/set_admin <your_username>` or `/set_registrator <your_username>`
   - You need at least Registrator permissions to register channels

#### 5. **Register Channels**
   - Go to the channel you want to link on **your server** and run: `/register_channel`
   - Go to the channel you want to link on **the other server** and run: `/register_channel`
   - ⚠️ **Important**: The same user must register all channels that will be linked together

#### 6. **Link the Channels**
   - In one of your registered channels, run:
     ```
     /link_channel <other_server_id> <other_channel_id> <group_name>
     ```

### Example
```
Server A Admin: /set_superadmin
Server A Admin: /set_registrator @UserB
UserB in Server A: /register_channel
UserB in Server B: /register_channel
UserB in Server A: /link_channel 123456789 987654321 "my-bridge"
✅ Channels are now linked!
```

### ⚠️ Important Notes
- **Same User Requirement**: All linked channels must be registered by the same user
- **Minimum 2 Channels**: Groups need at least 2 channels to function
- **Cross-Server Friendly**: You can link channels across any number of servers
- **Temporary Permissions**: Registrator permissions are usually temporary and removed after linking


### Data Storage
- **JSON Files**: User roles, channel registration, linking configuration
- **MongoDB**: Message relationships for reply tracking (no content stored)

### Security
- Permission-based access control
- Server isolation (admins only manage their own servers)
- Loop prevention (ignores bot/webhook messages)

---

Made with ❤️ for seamless Discord communication
