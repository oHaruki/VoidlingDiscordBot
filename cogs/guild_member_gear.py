import discord
from discord import app_commands
from discord.ext import commands
import mysql.connector
import os
import random

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
        # Generate text content for the current page
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_members = self.members[start:end]

        # Header
        text = "**Guild Members List**\n"
        text += "```diff\n"  # Use 'diff' to leverage color highlighting for all content
        text += f" Name           | Gear Score     | Class          | Main Hand      | Offhand       \n"
        text += "-" * 78 + "\n"

        # Add each member's information as a row
        for member in page_members:
            class_prefix = ""
            if member['class'] == "Healer":
                class_prefix = "+"
            elif member['class'] == "DPS":
                class_prefix = "-"
            elif member['class'] == "Tank":
                class_prefix = "#"  # Use # to give Tanks a distinct color, often gray

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
        self.db_connection = mysql.connector.connect(**DB_CONFIG)
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

        guild_id = interaction.guild.id

        cursor = self.db_connection.cursor()
        query = '''
            REPLACE INTO guild_members (discord_id, guild_id, ingame_name, gear_score, class, main_hand, offhand) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        '''
        cursor.execute(query, (interaction.user.id, guild_id, ingame_name, gear_score, guild_class, main_hand, offhand))
        cursor.close()
        self.db_connection.commit()
        await interaction.response.send_message("Your guild member information has been added/updated successfully.", ephemeral=True)

    @app_commands.command(name="guildmembers", description="Display a paginated list of guild members sorted by gear score.")
    async def guildmembers(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id

        cursor = self.db_connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM guild_members WHERE guild_id = %s ORDER BY gear_score DESC", (guild_id,))
        members = cursor.fetchall()
        cursor.close()

        if not members:
            await interaction.response.send_message("No guild members found.", ephemeral=True)
            return

        view = PagedGuildMembersView(members)
        await interaction.response.send_message(content=view.get_page_text(), view=view)

    @app_commands.command(name="manage_fake_entries", description="Add or delete fake guild member entries.")
    @app_commands.describe(action="Choose 'add' to add fake entries or 'delete' to delete them.")
    async def manage_fake_entries(self, interaction: discord.Interaction, action: str):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("Only the server owner can use this command.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        cursor = self.db_connection.cursor()

        if action.lower() == "add":
            # Insert 45 fake entries
            classes = ["Healer", "DPS", "Tank"]
            weapons = ["Staff", "Dagger", "SwordAndShield", "Greatsword", "Long Bow", "Crossbow", "WandAndTome"]

            for i in range(1, 46):
                ingame_name = f"FakeUser{i}"
                gear_score = random.randint(1000, 4000)
                guild_class = random.choice(classes)
                main_hand = random.choice(weapons)
                offhand = random.choice(weapons)

                query = '''
                    REPLACE INTO guild_members (discord_id, guild_id, ingame_name, gear_score, class, main_hand, offhand) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                '''
                cursor.execute(query, (100000 + i, guild_id, ingame_name, gear_score, guild_class, main_hand, offhand))

            self.db_connection.commit()
            await interaction.response.send_message("Inserted 45 fake entries successfully.", ephemeral=True)

        elif action.lower() == "delete":
            # Delete all fake entries where the discord_id is in the range 100001 - 100045
            try:
                delete_query = '''
                    DELETE FROM guild_members
                    WHERE guild_id = %s AND discord_id >= 100001 AND discord_id <= 100045
                '''
                cursor.execute(delete_query, (guild_id,))
                self.db_connection.commit()
                await interaction.response.send_message("Deleted 45 fake entries successfully.", ephemeral=True)
            except mysql.connector.Error as err:
                await interaction.response.send_message(f"Error deleting fake entries: {err}", ephemeral=True)

        else:
            await interaction.response.send_message("Invalid action. Use 'add' to insert fake entries or 'delete' to remove them.", ephemeral=True)

        cursor.close()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild_id = member.guild.id

        cursor = self.db_connection.cursor()
        cursor.execute("DELETE FROM guild_members WHERE discord_id = %s AND guild_id = %s", (member.id, guild_id))
        cursor.close()
        self.db_connection.commit()

async def setup(bot):
    await bot.add_cog(GuildMemberGear(bot))
