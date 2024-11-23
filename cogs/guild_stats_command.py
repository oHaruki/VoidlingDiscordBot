import discord
from discord import app_commands
from discord.ext import commands
import mysql.connector
import os
from collections import Counter
from mysql.connector import pooling

# Database connection configuration using environment variables
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

# Improved database connection management with pooling and reconnection
class DatabaseManager:
    def __init__(self, config):
        self.config = config
        self.pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **config)

    def get_connection(self):
        try:
            connection = self.pool.get_connection()
            connection.ping(reconnect=True)  # Ensure the connection is active
            return connection
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return None

# Initialize the DatabaseManager
db_manager = DatabaseManager(DB_CONFIG)

class GuildStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="guild_stats", description="Display stats about your guild members.")
    async def guild_stats(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id

        db_connection = db_manager.get_connection()
        if not db_connection:
            await interaction.response.send_message(
                "Database connection could not be established. Please try again later.", ephemeral=True
            )
            return

        cursor = db_connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM guild_members WHERE guild_id = %s", (guild_id,))
            members = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            await interaction.response.send_message("An error occurred while accessing the database. Please try again later.", ephemeral=True)
            return
        finally:
            cursor.close()
            db_connection.close()

        if not members:
            await interaction.response.send_message("No guild members found.", ephemeral=True)
            return

        # Calculate average gear score
        total_gear_score = sum(member['gear_score'] for member in members)
        average_gear_score = round(total_gear_score / len(members))

        # Count classes
        class_counts = Counter(member['class'] for member in members)

        # Count weapon combinations (regardless of order)
        weapon_combos = Counter(
            tuple(sorted((member['main_hand'], member['offhand']))) for member in members
        )

        # Sort weapon combinations by name
        sorted_weapon_combos = sorted(weapon_combos.items())

        # Create an embed for the stats
        embed = discord.Embed(title=f"Guild Statistics for {interaction.guild.name}", color=discord.Color.blue())
        embed.add_field(name="💡 Average Gear Score", value=f"{average_gear_score}", inline=False)
        embed.add_field(
            name="🎖 Class Distribution", 
            value=f"💖 Healers: {class_counts['Healer']}\n🔥 DPS: {class_counts['DPS']}\n🛡 Tanks: {class_counts['Tank']}", 
            inline=False
        )
        
        # Weapon Combos
        weapon_combos_text = "\n".join([f"🏹 {main} & {offhand}: {count}" for (main, offhand), count in sorted_weapon_combos])
        embed.add_field(name="🗠 Weapon Combinations", value=weapon_combos_text if weapon_combos_text else "None", inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(GuildStats(bot))
