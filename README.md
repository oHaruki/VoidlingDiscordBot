# Throne and Liberty Guild Bot

## Overview
This bot is designed to manage and track guild members within a Discord server. It allows users to register their in-game information, including gear score, class, and weapons, and displays this information in an organized manner. Additionally, it provides statistics about guild members such as the average gear score and class distribution.

## Features
- **Add Guild Member Information**: Users can add or update their in-game details (gear score, class, weapons) using commands.
- **Paginated Member List**: Displays a list of all guild members with their information in a paginated format.
- **Guild Statistics**: Provides statistics such as the average gear score, class distribution, and weapon combinations used by guild members.
- **Automatic Cleanup**: Removes members from the database when they leave the Discord server.

## Prerequisites
- Python 3.8 or above
- A MySQL database
- Discord Developer Account (to create a bot and get a token)

## Setup Instructions

### 1. Clone the Repository
First, clone this repository to your local machine:
```sh
git clone <repository-url>
cd <repository-folder>
```

### 2. Install Dependencies
Install the required dependencies using pip:
```sh
pip install -r requirements.txt
```

### 3. Set Up the MySQL Database
Create a MySQL database and user for the bot. The bot requires the following columns in a table called `guild_members`:
- `discord_id` (BIGINT, Primary Key)
- `guild_id` (BIGINT)
- `ingame_name` (VARCHAR)
- `gear_score` (INT)
- `class` (ENUM: 'Healer', 'DPS', 'Tank')
- `main_hand` (ENUM: 'Staff', 'Dagger', 'SwordAndShield', 'Greatsword', 'Long Bow', 'Crossbow', 'WandAndTome')
- `offhand` (ENUM: 'Staff', 'Dagger', 'SwordAndShield', 'Greatsword', 'Long Bow', 'Crossbow', 'WandAndTome')

### 4. Configure Environment Variables
Create a `.env` file in the project root (or use the provided `token.env` template). Add the following environment variables:
```env
DISCORD_BOT_TOKEN=<your-discord-bot-token>
DB_HOST=<your-database-host>
DB_USER=<your-database-user>
DB_PASSWORD=<your-database-password>
DB_NAME=<your-database-name>
```

### 5. Run the Bot
To run the bot, use the following command:
```sh
python bot.py
```

## Commands
- **/add_member**: Add or update your guild member gear information.
  - **Parameters**: `ingame_name`, `gear_score`, `guild_class`, `main_hand`, `offhand`
- **/guildmembers**: Display a paginated list of guild members sorted by gear score.
- **/guild_stats**: Display statistics about guild members including average gear score, class distribution, and weapon combinations.
- **!reload <cog_name>**: Reloads the specified cog (for server administrators).

## File Structure
- **bot.py**: The main entry point for the bot.
- **cogs/**: Contains individual features of the bot as separate modules.
  - **drops.py**: Manages drop-related functionalities.
  - **guild_member_gear.py**: Handles adding/updating guild member information and viewing member lists.
  - **guild_stats_command.py**: Handles the `/guild_stats` command.
- **token.env**: Stores environment variables for sensitive information.

## Notes
- The bot uses a MySQL database to store guild member information, so ensure your database is properly configured.
- Each Discord server that the bot is used in will have its data stored separately based on the server ID.

## Contributing
Feel free to open issues and submit pull requests for new features, improvements, or bug fixes.

## License
This project is open-source and available under the MIT License.

