import discord
from discord.ext import commands
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

class BossScheduleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.boss_times = [
            (13, "2 Peace Boss, 1 Conflict Boss"),
            (16, "2 Peace Boss, 1 Conflict Boss"),
            (20, "4 Peace Boss, 3 Conflict Boss"),
            (22, "3 Peace Boss, 2 Conflict Boss"),
            (1, "2 Peace Boss, 2 Conflict Boss")
        ]
        self.tz = pytz.timezone('Europe/Berlin')
        self.archboss_cycle_state = self.load_archboss_cycle_state()

    def load_archboss_cycle_state(self):
        # Retrieve the current active cycle state with status=1
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT cycle_state FROM archboss_cycle WHERE status = 1 LIMIT 1")
                result = cursor.fetchone()
                if result:
                    return result['cycle_state']
                # If no active cycle is found, set the first row as active (Conflict by default)
                cursor.execute("UPDATE archboss_cycle SET status = 1 WHERE id = 1")
                connection.commit()
                return "Conflict"  # Default to Conflict if no status is active
        except Error as e:
            print(f"Error while loading archboss cycle state: {e}")
        finally:
            if connection.is_connected():
                connection.close()
        return "Conflict"

    def update_archboss_cycle_state(self, next_archboss_time):
        # Shift the active cycle to the next row after each Archboss event
        now = datetime.now(self.tz)
        if now >= next_archboss_time:
            try:
                connection = mysql.connector.connect(**DB_CONFIG)
                if connection.is_connected():
                    cursor = connection.cursor(dictionary=True)
                    # Find the current active row
                    cursor.execute("SELECT id FROM archboss_cycle WHERE status = 1 LIMIT 1")
                    current_row = cursor.fetchone()
                    
                    if current_row:
                        current_id = current_row['id']
                        next_id = current_id + 1 if current_id < 4 else 1  # Wrap around to the first row
                        # Update the cycle state
                        cursor.execute("UPDATE archboss_cycle SET status = 0 WHERE id = %s", (current_id,))
                        cursor.execute("UPDATE archboss_cycle SET status = 1 WHERE id = %s", (next_id,))
                        connection.commit()
                        # Load the new cycle state
                        cursor.execute("SELECT cycle_state FROM archboss_cycle WHERE id = %s", (next_id,))
                        new_cycle = cursor.fetchone()
                        self.archboss_cycle_state = new_cycle['cycle_state'] if new_cycle else "Conflict"
            except Error as e:
                print(f"Error while updating archboss cycle state: {e}")
            finally:
                if connection.is_connected():
                    connection.close()

    def get_guild_settings(self, guild_id):
        # Retrieve guild settings from the database
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

    def get_next_boss_info(self):
        now = datetime.now(self.tz)
        for hour, info in self.boss_times:
            boss_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if boss_time > now:
                return boss_time, info
        # If no boss time is found today, return the midnight boss time tomorrow if it exists
        next_day = now + timedelta(days=1)
        midnight_boss = next((time for time in self.boss_times if time[0] == 0), None)
        if midnight_boss:
            return next_day.replace(hour=0, minute=0, second=0, microsecond=0), midnight_boss[1]
        # Otherwise, return the first boss time of the day
        return next_day.replace(hour=self.boss_times[0][0], minute=0, second=0, microsecond=0), self.boss_times[0][1]

    def get_next_archboss_info(self):
        now = datetime.now(self.tz)
        # Find the next Wednesday or Saturday
        next_wednesday = now + timedelta((2 - now.weekday()) % 7)
        next_saturday = now + timedelta((5 - now.weekday()) % 7)
        
        # Determine which is sooner and set the time to 20:00
        if next_wednesday < next_saturday:
            next_archboss_date = next_wednesday
        else:
            next_archboss_date = next_saturday
        
        next_archboss_time = next_archboss_date.replace(hour=20, minute=0, second=0, microsecond=0)
        return next_archboss_time, self.archboss_cycle_state

    @app_commands.command(name="boss_schedule", description="Displays the upcoming boss spawn schedule.")
    async def boss_schedule(self, interaction: discord.Interaction):
        next_boss_time, next_boss_info = self.get_next_boss_info()
        next_archboss_time, next_archboss_info = self.get_next_archboss_info()
        settings = self.get_guild_settings(interaction.guild.id)
        role_mention = f"<@&{settings['role_id']}>" if settings else "No role set"

        # Embed formatting with corrected newlines
        embed = discord.Embed(title="ðŸ•’ Upcoming Boss Spawn Schedule", color=discord.Color.green())
        embed.add_field(
            name="Next Boss",
            value=f"**Time**: <t:{int(next_boss_time.timestamp())}:R>\n**Boss**: {next_boss_info}",
            inline=False
        )

        # Determine emoji for Archboss type
        archboss_emoji = "ðŸ”´" if "Conflict" in next_archboss_info else "ðŸ”µ"
        if next_archboss_time and next_archboss_time < next_boss_time:
            embed.add_field(
                name=f"âš”ï¸ Next Archboss (High Priority!) {archboss_emoji}",
                value=f"**Time**: <t:{int(next_archboss_time.timestamp())}:R>\n**Boss**: {next_archboss_info}",
                inline=False
            )
        else:
            embed.add_field(
                name=f"Next Archboss {archboss_emoji}",
                value=f"**Time**: <t:{int(next_archboss_time.timestamp())}:R>\n**Boss**: {next_archboss_info}",
                inline=False
            )

        embed.add_field(
            name="Boss Spawn Reminder Role",
            value=(f"{role_mention}\nReact with the emoji below to access the reminder!"),
            inline=False
        )
        embed.set_thumbnail(url="https://haruki.s-ul.eu/fjEy0RW7")
        embed.set_footer(text="All times are in Berlin Standard Time (CET/CEST).")

        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        await message.add_reaction("â°")
        reaction = discord.utils.get(message.reactions, emoji="â°")
        if reaction and reaction.me:
            await reaction.remove(self.bot.user)

async def setup(bot):
    await bot.add_cog(BossScheduleCog(bot))