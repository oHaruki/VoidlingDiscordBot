import discord
from discord.ext import commands
from discord import app_commands
import mysql.connector
import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

class BossTimerRoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_role_id(self, guild_id):
        # Connect to the MySQL database to retrieve the role ID
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        query = "SELECT role_id FROM guild_settings WHERE guild_id = %s"
        cursor.execute(query, (guild_id,))
        result = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        return int(result[0]) if result else None

    @app_commands.command(name="subscribe", description="Subscribe to the Boss Timer role")
    async def subscribe(self, interaction: discord.Interaction):
        # Fetch the role ID for the server from the database
        role_id = self.get_role_id(interaction.guild.id)
        if not role_id:
            await interaction.response.send_message("Boss Timer role not set up in this server.", ephemeral=True)
            return

        # Retrieve the role from the guild
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("Role not found. Please contact an admin.", ephemeral=True)
            return

        # Add the role to the user if they don't have it
        if role in interaction.user.roles:
            await interaction.response.send_message("You are already subscribed to Boss Timer.", ephemeral=True)
        else:
            try:
                await interaction.user.add_roles(role, reason="Subscribed to Boss Timer role")
                await interaction.response.send_message("You have been subscribed to Boss Timer.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("I don't have permission to manage roles. Please make sure I have the appropriate permissions and try again.", ephemeral=True)
            except discord.HTTPException:
                await interaction.response.send_message("An error occurred while trying to assign the role. Please try again later.", ephemeral=True)

    @app_commands.command(name="unsubscribe", description="Unsubscribe from the Boss Timer role")
    async def unsubscribe(self, interaction: discord.Interaction):
        # Fetch the role ID for the server from the database
        role_id = self.get_role_id(interaction.guild.id)
        if not role_id:
            await interaction.response.send_message("Boss Timer role not set up in this server.", ephemeral=True)
            return

        # Retrieve the role from the guild
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("Role not found. Please contact an admin.", ephemeral=True)
            return

        # Remove the role from the user if they have it
        if role in interaction.user.roles:
            try:
                await interaction.user.remove_roles(role, reason="Unsubscribed from Boss Timer role")
                await interaction.response.send_message("You have been unsubscribed from Boss Timer.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("I don't have permission to manage roles. Please make sure I have the appropriate permissions and try again.", ephemeral=True)
            except discord.HTTPException:
                await interaction.response.send_message("An error occurred while trying to remove the role. Please try again later.", ephemeral=True)
        else:
            await interaction.response.send_message("You are not subscribed to Boss Timer.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BossTimerRoleCog(bot))