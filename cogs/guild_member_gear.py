import discord
from discord import app_commands
from discord.ext import commands
import mysql.connector
from mysql.connector import pooling
import os

# Database connection configuration using environment variables
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

# List of valid weapon options
VALID_WEAPONS = [
    "Staff", "Dagger", "SwordAndShield", "Greatsword", "Long Bow", "Crossbow", "WandAndTome"
]

class PagedGuildMembersView(discord.ui.View):
    def __init__(self, members, items_per_page=10):
        super().__init__()
        self.members = members
        self.items_per_page = items_per_page
        self.current_page = 0
        self.update_buttons()

    def update_buttons(self):
        self.previous_button.disabled = self.current_page <= 0
        self.next_button.disabled = self.current_page >= (len(self.members) - 1) // self.items_per_page

    def get_page_text(self):
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_members = self.members[start:end]

        text = "**Guild Members List**\n"
        text += "```diff\n"
        text += f" Name           | Gear Score     | Class          | Main Hand      | Offhand       \n"
        text += "-" * 78 + "\n"

        for member in page_members:
            class_prefix = ""
            if member['class'] == "Healer":
                class_prefix = "+"
            elif member['class'] == "DPS":
                class_prefix = "-"
            elif member['class'] == "Tank":
                class_prefix = "#"

            text += (
                f"{class_prefix}{member['ingame_name']:<15}| "
                f"{member['gear_score']:<15}| "
                f"{class_prefix}{member['class']:<15}| "
                f"{member['main_hand']:<15}| "
                f"{member['offhand']:<15}\n"
            )

        text += "```"
        text += f"Page {self.current_page + 1} of {(len(self.members) - 1) // self.items_per_page + 1}"

        return text

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(content=self.get_page_text(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < (len(self.members) - 1) // self.items_per_page:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(content=self.get_page_text(), view=self)

class GuildMemberGear(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_connection = db_manager.get_connection()
        self.create_table()

    def create_table(self):
        cursor = self.db_connection.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS guild_members (
                discord_id BIGINT,
                guild_id BIGINT,
                ingame_name VARCHAR(255),
                gear_score INT,
                class ENUM('Healer', 'DPS', 'Tank'),
                main_hand ENUM('Staff', 'Dagger', 'SwordAndShield', 'Greatsword', 'Long Bow', 'Crossbow', 'WandAndTome'),
                offhand ENUM('Staff', 'Dagger', 'SwordAndShield', 'Greatsword', 'Long Bow', 'Crossbow', 'WandAndTome'),
                PRIMARY KEY (discord_id, guild_id)
            )
            '''
        )
        cursor.close()
        self.db_connection.commit()

    @app_commands.command(name="add_member", description="Add or update your guild member gear information.")
    @app_commands.describe(
        ingame_name="Your in-game name", 
        gear_score="Your current gear score", 
        guild_class="Choose your class", 
        main_hand="Main hand weapon", 
        offhand="Offhand weapon"
    )
    async def add_member(self, interaction: discord.Interaction, ingame_name: str, gear_score: int, 
                         guild_class: str, main_hand: str, offhand: str):
        if main_hand not in VALID_WEAPONS:
            await interaction.response.send_message(
                f"Invalid main hand weapon! Please choose from: {', '.join(VALID_WEAPONS)}", ephemeral=True
            )
            return
        if offhand not in VALID_WEAPONS:
            await interaction.response.send_message(
                f"Invalid offhand weapon! Please choose from: {', '.join(VALID_WEAPONS)}", ephemeral=True
            )
            return

        valid_classes = ["Healer", "DPS", "Tank"]
        if guild_class not in valid_classes:
            await interaction.response.send_message(
                f"Invalid class! Please choose from: {', '.join(valid_classes)}", ephemeral=True
            )
            return

        guild_id = interaction.guild.id

        if not self.db_connection.is_connected():
            self.db_connection = db_manager.get_connection()

        if not self.db_connection:
            await interaction.response.send_message(
                "Database connection could not be established. Please try again later.", ephemeral=True
            )
            return

        cursor = self.db_connection.cursor()
        try:
            query = '''
                REPLACE INTO guild_members (discord_id, guild_id, ingame_name, gear_score, class, main_hand, offhand) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(query, (interaction.user.id, guild_id, ingame_name, gear_score, guild_class, main_hand, offhand))
            self.db_connection.commit()
            await interaction.response.send_message("Your guild member information has been added/updated successfully.", ephemeral=True)
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            await interaction.response.send_message("An error occurred while accessing the database. Please try again later.", ephemeral=True)
        finally:
            cursor.close()

    @app_commands.command(name="guildmembers", description="Display a paginated list of guild members sorted by gear score.")
    async def guildmembers(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id

        cursor = self.db_connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM guild_members WHERE guild_id = %s ORDER BY gear_score DESC", (guild_id,))
        members = cursor.fetchall()
        cursor.close()

        if not members:
            await interaction.response.send_message("No members found in the database.", ephemeral=True)
            return

        view = PagedGuildMembersView(members)
        await interaction.response.send_message(content=view.get_page_text(), view=view)

    @app_commands.command(name="remove_member", description="Remove a guild member from the database (only server owner can use).")
    @app_commands.describe(ingame_name="The in-game name of the member to remove.")
    async def remove_member(self, interaction: discord.Interaction, ingame_name: str):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "You do not have permission to use this command. Only the server owner can remove members.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id

        if not self.db_connection.is_connected():
            self.db_connection = db_manager.get_connection()

        if not self.db_connection:
            await interaction.response.send_message(
                "Database connection could not be established. Please try again later.",
                ephemeral=True
            )
            return

        cursor = self.db_connection.cursor()
        try:
            cursor.execute("SELECT * FROM guild_members WHERE ingame_name = %s AND guild_id = %s", (ingame_name, guild_id))
            member = cursor.fetchone()

            if not member:
                await interaction.response.send_message(
                    f"No member found with the in-game name '{ingame_name}' in this guild.",
                    ephemeral=True
                )
                return

            cursor.execute("DELETE FROM guild_members WHERE ingame_name = %s AND guild_id = %s", (ingame_name, guild_id))
            self.db_connection.commit()
            await interaction.response.send_message(f"Member with in-game name '{ingame_name}' has been successfully removed.", ephemeral=True)
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            await interaction.response.send_message("An error occurred while accessing the database. Please try again later.", ephemeral=True)
        finally:
            cursor.close()

async def setup(bot):
    await bot.add_cog(GuildMemberGear(bot))

class DatabaseManager:
    def __init__(self, config):
        self.config = config
        self.pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **config)

    def get_connection(self):
        try:
            connection = self.pool.get_connection()
            connection.ping(reconnect=True)
            return connection
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return None

db_manager = DatabaseManager(DB_CONFIG)
