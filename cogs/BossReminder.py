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

class BossReminder(commands.Cog):
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
            next_archboss_time = next_archboss_day.replace(hour=19, minute=0, second=0, microsecond=0)
            next_archboss_type = self.archboss_cycle[self.current_archboss_index % len(self.archboss_cycle)]
            return next_archboss_time, f"Archboss ({next_archboss_type})"
        return None, None

    def update_archboss_cycle(self):
        # Update the archboss index after an archboss spawn day has passed
        self.current_archboss_index = (self.current_archboss_index + 1) % len(self.archboss_cycle)

    def get_guild_settings(self, guild_id):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT channel_id, role_id FROM boss_settings WHERE guild_id = %s", (guild_id,))
            result = cursor.fetchone()
            return result
        except Error as e:
            print(f"Error reading data from MySQL table: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
        return None

    def save_guild_settings(self, guild_id, channel_id, role_id):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor()
            cursor.execute("REPLACE INTO boss_settings (guild_id, channel_id, role_id) VALUES (%s, %s, %s)", (guild_id, channel_id, role_id))
            connection.commit()
        except Error as e:
            print(f"Error writing data to MySQL table: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    @app_commands.command(name="boss_schedule", description="Show the upcoming boss spawn schedule.")
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
            value=f"{role_mention}\nReact with the emoji below to gain access to the reminder feature!",
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

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        if reaction.message.author == self.bot.user and str(reaction.emoji) == "⏰":
            guild = reaction.message.guild
            settings = self.get_guild_settings(guild.id)
            if settings:
                role = guild.get_role(settings['role_id'])
                if role:
                    if role in user.roles:
                        await user.remove_roles(role)
                        await user.send(f"You have been removed from the role: {role.name} for Boss Spawn Reminders.")
                    else:
                        await user.add_roles(role)
                        await user.send(f"You have been given the role: {role.name} for Boss Spawn Reminders.")

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        # Debugging log to check if the event triggers
        print(f"Reaction removed by {user.name} on message {reaction.message.id}")
        
        # Fetch the message if not cached
        if reaction.message.author.id != self.bot.user.id:
            try:
                reaction.message = await reaction.message.channel.fetch_message(reaction.message.id)
            except discord.NotFound:
                print("Message not found, skipping role removal.")
                return
            except discord.Forbidden:
                print("Missing permissions to fetch message.")
                return
            except discord.HTTPException as e:
                print(f"HTTP exception occurred while fetching message: {e}")
                return
        if user.bot:
            return

        if reaction.message.author.id == self.bot.user.id and str(reaction.emoji) == "⏰":
            # Debugging log to verify the role removal process
            print(f"Attempting to remove role from {user.name}")
            guild = reaction.message.guild
            settings = self.get_guild_settings(guild.id)
            if settings:
                role = guild.get_role(settings['role_id'])
                if role:
                    try:
                        await user.remove_roles(role)
                        await user.send(f"You have been removed from the role: {role.name} for Boss Spawn Reminders.")
                    except discord.Forbidden:
                        print(f"Failed to remove role from user {user.name}. Missing permissions.")
                    except discord.HTTPException as e:
                        print(f"HTTP error occurred while removing role from user {user.name}: {e}")

    @app_commands.command(name="set_boss_channel", description="Set the channel and role for boss reminders.")
    @commands.has_permissions(administrator=True)
    async def set_boss_channel(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
        self.save_guild_settings(interaction.guild.id, channel.id, role.id)
        await interaction.response.send_message(f"Boss reminder channel set to {channel.mention} and role set to {role.mention}.")

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
                if "Conflict" in next_archboss_info:
                    archboss_emoji = "🔴"
                else:
                    archboss_emoji = "🔵"
                
                # Regular boss reminder (10 minutes before spawn)
                if (next_boss_time - now).total_seconds() == 600:
                    await channel.send(f"⏰ {role} Reminder: The next boss spawn is in 10 minutes!\n**Boss**: {next_boss_info}")
                # Archboss reminder (15 minutes before spawn)
                if next_archboss_time and (next_archboss_time - now).total_seconds() == 900:
                    await channel.send(f"⚔️🔥 {role} **Archboss Reminder**: The Archboss will spawn in 15 minutes! {archboss_emoji}\n**Boss**: {next_archboss_info} (This is a high-priority event!)")
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
    await bot.add_cog(BossReminder(bot))
    # Sync application commands after adding the cog
    await bot.tree.sync()
