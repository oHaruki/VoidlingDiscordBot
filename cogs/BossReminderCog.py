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

    def get_next_boss_time(self):
        now = datetime.now(self.tz)
        daily_spawn_times = [12, 15, 19, 21, 0]  # Original spawn times for normal bosses
        for hour in daily_spawn_times:
            boss_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if boss_time > now:
                return boss_time, "Normal Boss"
        # If no boss time is found today, explicitly set the next boss time to midnight of the next day
        next_day = now + timedelta(days=1)
        next_boss_time = next_day.replace(hour=0, minute=0, second=0, microsecond=0)
        return next_boss_time, "Normal Boss"

    def get_next_archboss_time(self):
        now = datetime.now(self.tz)
        next_wednesday = now + timedelta((2 - now.weekday()) % 7)
        next_saturday = now + timedelta((5 - now.weekday()) % 7)
        next_archboss_day = next_wednesday if next_wednesday < next_saturday else next_saturday
        next_archboss_time = next_archboss_day.replace(hour=19, minute=0, second=0, microsecond=0)
        return next_archboss_time, "Archboss"

    @tasks.loop(minutes=1)
    async def boss_reminder_task(self):
        now = datetime.now(self.tz)
        for guild in self.bot.guilds:
            settings = self.get_guild_settings(guild.id)
            if not settings:
                continue

            channel = self.bot.get_channel(settings['channel_id'])
            role = f"<@&{settings['role_id']}>"

            # Get next boss and archboss times
            next_boss_time, boss_type = self.get_next_boss_time()
            next_archboss_time, archboss_type = self.get_next_archboss_time()

            # Check if it's time to send a reminder for normal bosses
            if (next_boss_time - now).total_seconds() <= 900:  # 15 minutes before the spawn
                if not self.last_boss_reminder_time or self.last_boss_reminder_time.date() != now.date() or now > self.last_boss_reminder_time:
                    self.last_boss_reminder_time = next_boss_time
                    if channel:
                        await channel.send(f"{role} Reminder: A **{boss_type}** will spawn in 15 minutes at <t:{int(next_boss_time.timestamp())}:t>.")

            # Check if it's time to send a reminder for archbosses
            if (next_archboss_time - now).total_seconds() <= 900:  # 15 minutes before the spawn
                if not self.last_archboss_reminder_time or self.last_archboss_reminder_time.date() != now.date() or now > self.last_archboss_reminder_time:
                    self.last_archboss_reminder_time = next_archboss_time
                    if channel:
                        await channel.send(f"{role} Reminder: An **{archboss_type}** will spawn in 15 minutes at <t:{int(next_archboss_time.timestamp())}:t>.")

    @boss_reminder_task.before_loop
    async def before_boss_reminder_task(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="set_boss_channel", description="Set the channel and role for boss reminders.")
    async def set_boss_channel(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
        self.save_guild_settings(interaction.guild.id, channel.id, role.id)
        await interaction.response.send_message(f"Boss reminder channel set to {channel.mention} and role set to {role.mention}.")

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

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.boss_reminder_task.is_running():
            self.boss_reminder_task.start()
            print("[INFO] Boss reminder task started.")

async def setup(bot):
    await bot.add_cog(BossReminderCog(bot))
