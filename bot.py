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
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_") and not filename.startswith("."):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"{filename} loaded successfully.")
            except Exception as e:
                print(f"Failed to load {filename}: {e}")

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

# Reload command to reload all cogs, and load new ones if they are not loaded
@bot.command()
async def reload(ctx):
    if ctx.author.id != 139769063948681217:
        await ctx.send("You do not have permission to use this command.")
        return
    try:
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_") and not filename.startswith("."):
                extension = f"cogs.{filename[:-3]}"
                if extension in bot.extensions:
                    await bot.unload_extension(extension)
                await bot.load_extension(extension)
        await ctx.send("Reloaded all extensions, including any new ones.")
    except Exception as e:
        await ctx.send(f"Error reloading extensions: {e}")

# Run the bot using the token from .env file
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
