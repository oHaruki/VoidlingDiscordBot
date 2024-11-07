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
        self.tz = pytz.timezone('Europe/Berlin')  # Setting timezone to Europe/Berlin
        self.last_boss_reminder_time = None  # Track last reminder for normal bosses
        self.last_archboss_reminder_time = None  # Track last reminder for Archbosses
        self.boss_reminder_task.start()

    def get_guild_settings(self, guild_id):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT channel_id, role_id FROM guild_settings WHERE guild_id = %s", (guild_id,))
                result = cursor.fetchone()
                return result
        except Error as e:
            print(f"[ERROR] Database connection failed: {e}")
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
                print(f"[INFO] Saved guild settings for guild {guild_id}.")
        except Error as e:
            print(f"[ERROR] Failed to save guild settings: {e}")
        finally:
            if connection.is_connected():
                connection.close()

    def get_next_boss_time(self):
        # Boss spawn times in Europe/Berlin timezone (original BST times)
        now = datetime.now(self.tz)
        daily_spawn_times = [12, 15, 19, 21, 0]  # Original BST/Europe/Berlin times for normal bosses
        for hour in daily_spawn_times:
            boss_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if boss_time > now:
                return boss_time, "Normal Boss"
        next_day = now + timedelta(days=1)
        next_boss_time = next_day.replace(hour=daily_spawn_times[0], minute=0, second=0, microsecond=0)
        return next_boss_time, "Normal Boss"

    def get_next_archboss_time(self):
        # Archboss spawn times in Europe/Berlin timezone (originally 19:00 BST)
        now = datetime.now(self.tz)
        days_until_next_archboss = (2 - now.weekday()) % 7 if now.weekday() <= 2 else (5 - now.weekday()) % 7
        next_archboss_day = now + timedelta(days=days_until_next_archboss)
        next_archboss_time = next_archboss_day.replace(hour=19, minute=0, second=0, microsecond=0)  # 19:00 Europe/Berlin

        # If today is Archboss day but after 19:00, move to the next spawn day
        if next_archboss_time <= now:
            next_archboss_time += timedelta(days=3 if next_archboss_time.weekday() == 2 else 4)
        
        return next_archboss_time, "Archboss"

    @app_commands.command(name="set_boss_channel", description="Set the channel and role for boss reminders.")
    @commands.has_permissions(administrator=True)
    async def set_boss_channel(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
        self.save_guild_settings(interaction.guild.id, channel.id, role.id)
        await interaction.response.send_message(f"Boss reminder channel set to {channel.mention} and role set to {role.mention}.")

    @tasks.loop(minutes=1)
    async def boss_reminder_task(self):
        now = datetime.now(self.tz)
        for guild in self.bot.guilds:
            settings = self.get_guild_settings(guild.id)
            if settings:
                channel = self.bot.get_channel(settings['channel_id'])
                role = f"<@&{settings['role_id']}>"

                if not channel:
                    print(f"[WARNING] Channel {settings['channel_id']} not found for guild {guild.id}.")
                    continue

                try:
                    # Calculate the next spawn times
                    next_boss_time, next_boss_info = self.get_next_boss_time()
                    next_archboss_time, next_archboss_info = self.get_next_archboss_time()

                    # Send a reminder 10 minutes before a normal boss if it hasn't already been sent
                    if (
                        550 <= (next_boss_time - now).total_seconds() <= 650
                        and next_boss_time != self.last_boss_reminder_time
                    ):
                        message = f"⏰ {role} Reminder: The next boss spawn is in 10 minutes! Boss: {next_boss_info}"
                        await channel.send(message)
                        self.last_boss_reminder_time = next_boss_time  # Update last reminder time
                        print(f"[INFO] Sent reminder for {next_boss_info} in guild {guild.id}.")

                    # Send a reminder 15 minutes before an Archboss if it hasn't already been sent
                    if (
                        850 <= (next_archboss_time - now).total_seconds() <= 950
                        and next_archboss_time != self.last_archboss_reminder_time
                    ):
                        archboss_emoji = "🔴" if "Conflict" in next_archboss_info else "🔵"
                        message = f"⚔️🔥 {role} Reminder: The next Archboss spawn is in 15 minutes! {archboss_emoji} Archboss: {next_archboss_info}"
                        await channel.send(message)
                        self.last_archboss_reminder_time = next_archboss_time  # Update last reminder time
                        print(f"[INFO] Sent reminder for Archboss in guild {guild.id}.")

                except Exception as e:
                    print(f"[ERROR] Reminder task error for guild {guild.id}: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.boss_reminder_task.is_running():
            self.boss_reminder_task.start()
            print("[INFO] Boss reminder task started.")

async def setup(bot):
    await bot.add_cog(BossReminderCog(bot))