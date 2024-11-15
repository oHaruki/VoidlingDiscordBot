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
        self.reminders_sent = {}  # Track sent reminders per guild and boss type
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
        daily_spawn_times = [13, 16, 20, 22, 1]  # Original spawn times for normal bosses
        for hour in daily_spawn_times:
            boss_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if boss_time > now:
                return boss_time, "Normal Boss"
        next_day = now + timedelta(days=1)
        next_boss_time = next_day.replace(hour=0, minute=0, second=0, microsecond=0)
        return next_boss_time, "Normal Boss"

    def get_next_archboss_time(self):
        now = datetime.now(self.tz)
        next_wednesday = now + timedelta((2 - now.weekday()) % 7)
        next_saturday = now + timedelta((5 - now.weekday()) % 7)
        archboss_times = [
            next_wednesday.replace(hour=20, minute=0, second=0, microsecond=0),
            next_saturday.replace(hour=20, minute=0, second=0, microsecond=0)
        ]
        for archboss_time in archboss_times:
            if archboss_time > now:
                return archboss_time, "Archboss"
        next_week_wednesday = next_wednesday + timedelta(weeks=1)
        return next_week_wednesday.replace(hour=19, minute=0, second=0, microsecond=0), "Archboss"

    @tasks.loop(minutes=1)
    async def boss_reminder_task(self):
        now = datetime.now(self.tz)
        next_boss_time, boss_type = self.get_next_boss_time()
        next_archboss_time, archboss_type = self.get_next_archboss_time()

        for guild in self.bot.guilds:
            guild_settings = self.get_guild_settings(guild.id)

            # Skip if the guild hasn't set up the channel and role in the database
            if not guild_settings:
                continue

            channel_id = guild_settings.get("channel_id")
            role_id = guild_settings.get("role_id")
            
            channel = guild.get_channel(channel_id) if channel_id else None
            role = guild.get_role(role_id) if role_id else None

            if guild.id not in self.reminders_sent:
                self.reminders_sent[guild.id] = {"Normal Boss": False, "Archboss": False}

            # Normal Boss Reminder
            if (next_boss_time - now).total_seconds() <= 900:  # 15 minutes before the spawn
                if not self.reminders_sent[guild.id]["Normal Boss"]:
                    self.reminders_sent[guild.id]["Normal Boss"] = True
                    if channel:
                        try:
                            await channel.send(f"{role.mention if role else ''} Reminder: A **{boss_type}** will spawn in 15 minutes at <t:{int(next_boss_time.timestamp())}:t>.")
                        except discord.Forbidden:
                            print(f"[ERROR] Missing access to channel {channel.id} in guild {guild.id}.")
                        except discord.HTTPException as e:
                            print(f"[ERROR] Failed to send message in guild {guild.id}: {e}")
            else:
                self.reminders_sent[guild.id]["Normal Boss"] = False

            # Archboss Reminder
            if (next_archboss_time - now).total_seconds() <= 900:  # 15 minutes before the spawn
                if not self.reminders_sent[guild.id]["Archboss"]:
                    self.reminders_sent[guild.id]["Archboss"] = True
                    if channel:
                        try:
                            await channel.send(f"{role.mention if role else ''} Reminder: An **{archboss_type}** will spawn in 15 minutes at <t:{int(next_archboss_time.timestamp())}:t>.")
                        except discord.Forbidden:
                            print(f"[ERROR] Missing access to channel {channel.id} in guild {guild.id}.")
                        except discord.HTTPException as e:
                            print(f"[ERROR] Failed to send message in guild {guild.id}: {e}")
            else:
                self.reminders_sent[guild.id]["Archboss"] = False

    @boss_reminder_task.before_loop
    async def before_boss_reminder_task(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="set_boss_channel", description="Set the channel and role for boss reminders.")
    async def set_boss_channel(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            if connection.is_connected():
                cursor = connection.cursor()
                cursor.execute("REPLACE INTO guild_settings (guild_id, channel_id, role_id) VALUES (%s, %s, %s)",
                               (interaction.guild.id, channel.id, role.id))
                connection.commit()
                await interaction.response.send_message(f"Boss reminder channel set to {channel.mention} with role {role.mention}.")
        except Error as e:
            print(f"[ERROR] Database connection failed: {e}")
            await interaction.response.send_message("Failed to set the boss reminder channel due to a database error.", ephemeral=True)
        finally:
            if connection.is_connected():
                connection.close()

async def setup(bot):
    await bot.add_cog(BossReminderCog(bot))