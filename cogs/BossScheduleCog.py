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
            (12, "2 Peace Boss, 1 Conflict Boss"),
            (15, "2 Peace Boss, 1 Conflict Boss"),
            (19, "4 Peace Boss, 3 Conflict Boss"),
            (21, "3 Peace Boss, 2 Conflict Boss"),
            (0, "2 Peace Boss, 2 Conflict Boss")
        ]
        self.archboss_cycle = ["Conflict Boss", "Peace Boss"]
        self.current_archboss_index = 1  # Start with index 1 as today we are at the last Peace Boss
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

    def get_next_boss_info(self):
        now = datetime.now(self.tz)
        for hour, info in self.boss_times:
            boss_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if boss_time > now:
                return boss_time, info
        # If no boss time is found today, return the first boss time tomorrow
        next_day = now + timedelta(days=1)
        return next_day.replace(hour=self.boss_times[0][0], minute=0, second=0, microsecond=0), self.boss_times[0][1]

    def get_next_archboss_info(self):
        now = datetime.now(self.tz)
        next_archboss_day = None
        # Find the next Wednesday or Saturday
        for i in range(7):
            potential_day = now + timedelta(days=i)
            if potential_day.weekday() in [2, 5]:  # Wednesday or Saturday
                next_archboss_day = potential_day
                break
        if next_archboss_day is not None:
            return next_archboss_day.replace(hour=19, minute=0, second=0, microsecond=0), self.archboss_cycle[self.current_archboss_index]
        return None, None

    @app_commands.command(name="boss_schedule", description="Displays the upcoming boss spawn schedule.")
    async def boss_schedule(self, interaction: discord.Interaction):
        next_boss_time, next_boss_info = self.get_next_boss_info()
        next_archboss_time, next_archboss_info = self.get_next_archboss_info()
        settings = self.get_guild_settings(interaction.guild.id)
        role_mention = f"<@&{settings['role_id']}>" if settings else "No role set"

        embed = discord.Embed(title="🕒 Upcoming Boss Spawn Schedule", color=discord.Color.green())
        embed.add_field(
            name="Next Boss",
            value=f"**Time**: <t:{int(next_boss_time.timestamp())}:R>\n**Boss**: {next_boss_info}",
            inline=False
        )

        # Add an emoji based on boss type
        if "Conflict" in next_archboss_info:
            archboss_emoji = "🔴"
        else:
            archboss_emoji = "🔵"

        if next_archboss_time and next_archboss_time < next_boss_time:
            embed.add_field(
                name=f"⚔️ Next Archboss (This is a high-priority event!) {archboss_emoji}",
                value=f"**Time**: <t:{int(next_archboss_time.timestamp())}:R>\n**Boss**: {next_archboss_info}",
                inline=False
            )
        else:
            embed.add_field(
                name=f"Next Archboss (Important!) {archboss_emoji}",
                value=f"**Time**: <t:{int(next_archboss_time.timestamp())}:R>\n**Boss**: {next_archboss_info}",
                inline=False
            )

        embed.add_field(
            name="Boss Spawn Reminder Role",
            value=(
                f"{role_mention}\n"
                "React with the emoji below to gain access to the reminder feature!"
            ),
            inline=False
        )

        embed.set_thumbnail(url="https://haruki.s-ul.eu/fjEy0RW7")
        embed.set_footer(text="All times are in Berlin Standard Time (CET/CEST).")
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        # React to the message to allow users to gain access to the reminder role
        await message.add_reaction("⏰")
        # Remove the bot's reaction to allow users to toggle the role
        reaction = discord.utils.get(message.reactions, emoji="⏰")
        if reaction and reaction.me:
            await reaction.remove(self.bot.user)

async def setup(bot):
    await bot.add_cog(BossScheduleCog(bot))
    await bot.tree.sync()