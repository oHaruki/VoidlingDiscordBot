# Throne and Liberty Discord Bot

## Overview

The Discord Bot is designed to manage and track guild members within a the Discord server. It allows users to register in-game information such as gear score, class, and weapons, and displays this information in an organized manner. Additionally, it provides valuable features for guild management, including guild member statistics, Boss voting, and welcoming new members.
It also has a built in Boss Timer + Reminder, for now it display not exact Boss Information till API from Amazon is being released.

## Features

- **Add Guild Member Information**: Users can add or update their in-game details (gear score, class, weapons) using commands.
- **Guild Member List**: Displays a list of all guild members with their information in a paginated format.
- **Guild Statistics**: Provides stats such as the average gear score, class distribution, and popular weapon combinations.
- **Automatic Cleanup**: Removes members from the database when they leave the Discord server.
- **Weekly Boss Tracker**: Tracks upcoming weekly boss events.
- **Ping Command**: Basic ping-pong command to check bot responsiveness.
- **Welcome Messages**: Sends a welcome message to new members who join the server.

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

The dependencies include:

- **discord.py**: Python wrapper for the Discord API
- **python-dotenv**: Loads environment variables from a `.env` file
- **mysql-connector-python**: MySQL driver for database communication
- **asyncpg**: Async driver for PostgreSQL (can be left out not needed atm)
- **psutil**: Cross-platform library for system information and process utilities

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

### Slash Commands (`/`)

- **/blessing**: Calc for Blessing with detailed Analysis when Blue or Purple Blessing is more efficent.
- **/boss\_schedule**: Displays Boss Timer
- **/add\_member**: Add or update your guild member gear information.
  - **Parameters**: `ingame_name`, `gear_score`, `guild_class`, `main_hand`, `offhand`
- **/guildmembers**: Display a paginated list of guild members sorted by gear score.
- **/guild\_stats**: Display statistics about guild members including average gear score, class distribution, and weapon combinations.
- **/post\_weekly\_bosses**: Starts a vote for the next Guild Bosses.
- **/results\_weekly\_bosses**: Gets the vote results for the enxt guild bosses.
- **/set\_welcome\_message**: Sets a welcome message for new Members joining the discord which is being dm'd
- **/preview\_welcome\_message**: Preview's welcome message
- **/post\_drops**: Post Guild drops that you got from Weekly Raids
- **/get\_votes**: Gets the votes from Weekly Raids
- **/manage\_fake\_entries**: Creates/Deletes fake guild member entries for testing purposes (admin-only).

### Prefix Commands (`!`)

- **!reload**: Reloads the specified cog (For Bot Owner Only, set ID in cog).
- **!ping**: Responds with "Pong!" to check if the bot is active and responsive.

## File Structure

- **bot.py**: The main entry point for the bot.
- **cogs/**: Contains individual features of the bot as separate modules.
  - **drops.py**: Manages drop-related functionalities.
  - **guild\_member\_gear.py**: Handles adding/updating guild member information and viewing member lists.
  - **guild\_stats\_command.py**: Handles the `/guild_stats` command.
  - **ping\_pong.py**: Implements the ping command.
  - **WeeklyGuildBoss.py**: Handles tracking and notifying about weekly boss events.
  - **WelcomeMessage.py**: Sends welcome messages to new server members.
- **token.env**: Stores environment variables for sensitive information.
- **requirements.txt**: Contains a list of required Python libraries.

## Notes

- The bot uses a MySQL database to store guild member information, so ensure your database is properly configured.
- Each Discord server that the bot is used in will have its data stored separately based on the server ID.

## Contributing

Feel free to open issues and submit pull requests for new features, improvements, or bug fixes.

## License

This project is open-source and available under the MIT License.
