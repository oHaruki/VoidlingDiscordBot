import discord
from discord import app_commands
from discord.ext import commands
import mysql.connector
import os
from collections import Counter

# Database connection configuration using environment variables
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

class GuildStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_connection = mysql.connector.connect(**DB_CONFIG)

    @app_commands.command(name="guild_stats", description="Display stats about your guild members.")
    async def guild_stats(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id

        cursor = self.db_connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM guild_members WHERE guild_id = %s", (guild_id,))
        members = cursor.fetchall()
        cursor.close()

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
