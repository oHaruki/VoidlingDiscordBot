import discord
from discord.ext import commands
import mysql.connector
import os

# Load DB config from environment variables
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

    @commands.command(name="subscribe")
    async def subscribe(self, ctx, role_name: str):
        if role_name.lower() != "bosstimer":
            await ctx.send("Invalid role. Please use `/subscribe bosstimer`.")
            return

        role_id = self.get_role_id(ctx.guild.id)
        if not role_id:
            await ctx.send("Boss Timer role not set up in this server.")
            return

        role = ctx.guild.get_role(role_id)
        if not role:
            await ctx.send("Role not found. Please contact an admin.")
            return

        if role in ctx.author.roles:
            await ctx.send("You are already subscribed to Boss Timer.")
        else:
            await ctx.author.add_roles(role)
            await ctx.send("You have been subscribed to Boss Timer.")

    @commands.command(name="unsubscribe")
    async def unsubscribe(self, ctx, role_name: str):
        if role_name.lower() != "bosstimer":
            await ctx.send("Invalid role. Please use `/unsubscribe bosstimer`.")
            return

        role_id = self.get_role_id(ctx.guild.id)
        if not role_id:
            await ctx.send("Boss Timer role not set up in this server.")
            return

        role = ctx.guild.get_role(role_id)
        if not role:
            await ctx.send("Role not found. Please contact an admin.")
            return

        if role in ctx.author.roles:
            await ctx.author.remove_roles(role)
            await ctx.send("You have been unsubscribed from Boss Timer.")
        else:
            await ctx.send("You are not subscribed to Boss Timer.")

async def setup(bot):
    await bot.add_cog(BossTimerRoleCog(bot))