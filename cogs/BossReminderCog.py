
import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import pytz
import os
import mysql.connector
from mysql.connector import Error

# Database connection configuration using environment variables
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

class BossReminderCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tz = pytz.timezone('Europe/Berlin')

    def get_guild_settings(self, guild_id):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT channel_id, role_id FROM guild_settings WHERE guild_id = %s", (guild_id,))
                result = cursor.fetchone()
                return result
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")
        finally:
            if connection.is_connected():
                connection.close()
        return None

    def save_guild_settings(self, guild_id, channel_id, role_id):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            if connection.is_connected():
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO guild_settings (guild_id, channel_id, role_id) "
                    "VALUES (%s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE channel_id=%s, role_id=%s",
                    (guild_id, channel_id, role_id, channel_id, role_id)
                )
                connection.commit()
        except Error as e:
            print(f"Error while saving guild settings to MySQL: {e}")
        finally:
            if connection.is_connected():
                connection.close()

    @app_commands.command(name="set_boss_channel", description="Set the channel and role for boss reminders.")
    @commands.has_permissions(administrator=True)
    async def set_boss_channel(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
        try:
            self.save_guild_settings(interaction.guild.id, channel.id, role.id)
            await interaction.response.send_message(f"Boss reminder channel set to {channel.mention} and role set to {role.mention}.")
        except Exception as e:
            await interaction.response.send_message("An error occurred while setting the boss channel.", ephemeral=True)
            print(f"Error in set_boss_channel: {e}")

    @commands.command(name="bosstest", help="Test the boss reminder feature.")
    async def bosstest(self, ctx):
        settings = self.get_guild_settings(ctx.guild.id)
        if not settings:
            await ctx.send("No boss reminder settings found for this server. Please set up the boss reminder channel and role first.")
            return

        channel = self.bot.get_channel(settings['channel_id'])
        role = f"<@&{settings['role_id']}>"
        await channel.send(f"🛠️ {role} This is a test reminder for the Boss Spawn feature.")

    @tasks.loop(minutes=1)
    async def boss_reminder_task(self):
        now = datetime.now(self.tz)
        for guild in self.bot.guilds:
            settings = self.get_guild_settings(guild.id)
            if settings:
                channel_id = settings['channel_id']
                role_id = settings['role_id']
                channel = self.bot.get_channel(channel_id)
                role = f"<@&{role_id}>"
                next_boss_time, next_boss_info = self.get_next_boss_info()
                next_archboss_time, next_archboss_info = self.get_next_archboss_info()

                # Determine the appropriate emoji for the Archboss
                archboss_emoji = "🔴" if "Conflict" in next_archboss_info else "🔵"
                
                # Regular boss reminder (10 minutes before spawn)
                if 590 <= (next_boss_time - now).total_seconds() <= 610:
                    message = f"⏰ {role} Reminder: The next boss spawn is in 10 minutes! Boss: {next_boss_info}"
                    await channel.send(message)
                
                # Archboss reminder (15 minutes before spawn)
                if next_archboss_time and 890 <= (next_archboss_time - now).total_seconds() <= 910:
                    message = f"⚔️🔥 {role} Archboss Reminder: The Archboss will spawn in 15 minutes! {archboss_emoji} Boss: {next_archboss_info} (This is a high-priority event!)"
                    await channel.send(message)
                    self.update_archboss_cycle()  # Update archboss type after a reminder

    @boss_reminder_task.before_loop
    async def before_boss_reminder_task(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.boss_reminder_task.is_running():
            # Start the boss reminder task loop
            self.boss_reminder_task.start()

async def setup(bot):
    await bot.add_cog(BossReminderCog(bot))
    await bot.tree.sync()
