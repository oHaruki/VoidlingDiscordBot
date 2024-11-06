import discord
from discord.ext import commands
import psutil
import platform
import time

class PingPong(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @commands.command(name="ping")
    async def ping(self, ctx):
        # Calculate bot latency (Ping)
        bot_latency = round(self.bot.latency * 1000, 2)  # Latency in milliseconds
        
        # Gather CPU and memory usage
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # Calculate uptime
        uptime_seconds = time.time() - self.start_time
        uptime_hours = round(uptime_seconds / 3600, 2)
        
        # Get Python version
        python_version = platform.python_version()
        
        # Get additional bot information
        guild_count = len(self.bot.guilds)  # Number of servers the bot is in
        user_count = len(set(self.bot.get_all_members()))  # Number of unique users the bot can interact with
        channel_count = sum(1 for _ in self.bot.get_all_channels())  # Number of channels the bot has access to
        disk_usage = psutil.disk_usage('/')
        disk_usage_percent = disk_usage.percent  # Disk usage percentage
        os_info = platform.system() + " " + platform.release()  # Operating system information

        # Create response message
        response = (f"Bot Latency: {bot_latency}ms\n"
                    f"CPU Usage: {cpu_usage}%\n"
                    f"Memory Usage: {memory_usage}%\n"
                    f"Disk Usage: {disk_usage_percent}%\n"
                    f"Uptime: {uptime_hours} hours\n"
                    f"Python Version: {python_version}\n"
                    f"Operating System: {os_info}\n"
                    f"Number of Servers: {guild_count}\n"
                    f"Number of Users: {user_count}\n"
                    f"Number of Channels: {channel_count}")
        
        await ctx.send(response)

async def setup(bot):
    await bot.add_cog(PingPong(bot))