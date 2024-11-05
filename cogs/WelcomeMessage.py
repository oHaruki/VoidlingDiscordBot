import discord
from discord.ext import commands
from discord import app_commands
import os
import mysql.connector
from concurrent.futures import ThreadPoolExecutor
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database connection configuration using environment variables
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

class WelcomeMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_connection = None
        self.executor = ThreadPoolExecutor()

    def create_connection(self):
        if self.db_connection is None or not self.db_connection.is_connected():
            try:
                logger.debug("Creating new database connection")
                self.db_connection = mysql.connector.connect(**DB_CONFIG)
                logger.debug("Database connection established successfully")
            except mysql.connector.Error as err:
                logger.error(f"Error connecting to the database: {err}")

    async def run_in_executor(self, func, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, func, *args)

    @commands.Cog.listener()
    async def on_ready(self):
        logger.debug("Bot is ready. Establishing database connection...")
        self.create_connection()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        logger.debug(f"New member joined: {member.name} ({member.id})")
        guild_id = member.guild.id
        self.create_connection()
        cursor = self.db_connection.cursor()
        try:
            cursor.execute(
                "SELECT message FROM welcome_messages WHERE guild_id = %s", (guild_id,)
            )
            result = cursor.fetchone()
            welcome_message = result[0] if result else None
            logger.debug(f"Fetched welcome message for guild {guild_id}: {welcome_message}")
        except mysql.connector.Error as err:
            logger.error(f"Error fetching welcome message: {err}")
            welcome_message = None
        finally:
            cursor.close()
        
        if welcome_message:
            try:
                await member.send(welcome_message)
                logger.debug(f"Sent welcome message to {member.name}")
            except discord.Forbidden:
                logger.warning(f"Unable to DM {member.name}, maybe they have DMs disabled.")

    @app_commands.command(name="set_welcome_message", description="Set the welcome message for new members.")
    @app_commands.describe(message="The welcome message to send to new members.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_welcome_message(self, interaction: discord.Interaction, message: str):
        """
        Set the welcome message for new members joining the Discord server.
        """
        guild_id = interaction.guild_id
        logger.debug(f"Setting welcome message for guild {guild_id} by {interaction.user.name}")
        await self.run_in_executor(self.create_connection)
        success = await self.run_in_executor(self.save_welcome_message, guild_id, message)
        if success:
            await interaction.response.send_message("Welcome message set successfully for this server.", ephemeral=True)
        else:
            await interaction.response.send_message("Failed to set the welcome message. Please try again later.", ephemeral=True)

    @set_welcome_message.error
    async def set_welcome_message_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.errors.MissingPermissions):
            if not interaction.response.is_done():
                await interaction.response.send_message("You do not have permission to use this command. Only administrators can set the welcome message.", ephemeral=True)
            else:
                await interaction.followup.send("You do not have permission to use this command. Only administrators can set the welcome message.", ephemeral=True)

    def save_welcome_message(self, guild_id, message):
        cursor = None
        try:
            if not self.db_connection or not self.db_connection.is_connected():
                logger.error("Database connection is not established or has been lost.")
                return False

            cursor = self.db_connection.cursor()
            logger.debug(f"Executing INSERT/UPDATE for guild_id {guild_id}")
            cursor.execute(
                """
                INSERT INTO welcome_messages (guild_id, message) 
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE message = %s
                """,
                (guild_id, message, message)
            )
            self.db_connection.commit()
            affected_rows = cursor.rowcount
            logger.debug(f"Saved welcome message for guild {guild_id}, affected rows: {affected_rows}")
            if affected_rows == 0:
                logger.error("No rows were affected. This could mean the INSERT/UPDATE statement failed or there was no change.")
            return affected_rows > 0
        except mysql.connector.Error as err:
            logger.error(f"Error saving welcome message: {err}")
            return False
        finally:
            if cursor:
                cursor.close()

    @app_commands.command(name="preview_welcome_message", description="Preview the welcome message for this server.")
    async def preview_welcome_message(self, interaction: discord.Interaction):
        """
        Preview the welcome message that will be sent to new members.
        """
        guild_id = interaction.guild_id
        logger.debug(f"Previewing welcome message for guild {guild_id} by {interaction.user.name}")
        await self.run_in_executor(self.create_connection)
        welcome_message = await self.run_in_executor(self.get_welcome_message, guild_id)
        
        if welcome_message:
            try:
                await interaction.user.send(welcome_message)
                await interaction.response.send_message("The welcome message has been sent to your DMs.", ephemeral=True)
                logger.debug(f"Sent preview of welcome message to {interaction.user.name}")
            except discord.Forbidden:
                await interaction.response.send_message("Unable to send you a DM. Please check your privacy settings.", ephemeral=True)
                logger.warning(f"Unable to DM {interaction.user.name}, maybe they have DMs disabled.")
        else:
            await interaction.response.send_message("No welcome message set for this server.", ephemeral=True)
            logger.debug(f"No welcome message set for guild {guild_id}")

    def get_welcome_message(self, guild_id):
        cursor = None
        try:
            if not self.db_connection or not self.db_connection.is_connected():
                logger.error("Database connection is not established or has been lost.")
                return None

            cursor = self.db_connection.cursor()
            cursor.execute(
                "SELECT message FROM welcome_messages WHERE guild_id = %s", (guild_id,)
            )
            result = cursor.fetchone()
            logger.debug(f"Fetched welcome message for guild {guild_id}: {result}")
            return result[0] if result else None
        except mysql.connector.Error as err:
            logger.error(f"Error fetching welcome message: {err}")
            return None
        finally:
            if cursor:
                cursor.close()

async def setup(bot):
    await bot.add_cog(WelcomeMessage(bot))
    # Sync commands if not already synced
    if not hasattr(bot, 'synced') or not bot.synced:
        await bot.tree.sync()
        bot.synced = True