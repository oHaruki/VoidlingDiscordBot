import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

# Load environment variables from the specified .env file
load_dotenv("token.env")

# Debugging: Print database environment variables to confirm they are loaded
print("DB_HOST:", os.getenv("DB_HOST"))
print("DB_USER:", os.getenv("DB_USER"))
print("DB_PASSWORD:", os.getenv("DB_PASSWORD"))
print("DB_NAME:", os.getenv("DB_NAME"))

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    # Load the cogs
    try:
        await bot.load_extension("cogs.drops")
        print("Drops cog loaded successfully.")
    except Exception as e:
        print(f"Failed to load Drops cog: {e}")

    try:
        await bot.load_extension("cogs.guild_member_gear")  # Load the Guild Member Gear cog
        print("Guild Member Gear cog loaded successfully.")
    except Exception as e:
        print(f"Failed to load Guild Member Gear cog: {e}")

    try:
        await bot.load_extension("cogs.guild_stats_command")  # Load the new Guild Stats cog
        print("Guild Stats cog loaded successfully.")
    except Exception as e:
        print(f"Failed to load Guild Stats cog: {e}")

    # Sync commands globally (for all servers the bot is in)
    try:
        await bot.tree.sync()
        print("Commands synced globally.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    # Debug: Print all registered commands
    print("Registered commands:")
    for command in bot.tree.get_commands():
        print(f"- {command.name}: {command.description}")

# Run the bot using the token from .env file
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
