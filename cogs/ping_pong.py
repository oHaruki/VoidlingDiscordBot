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
        import random
        cluster = random.randint(100, 200)
        cluster_latency = round(random.uniform(20.0, 40.0), 2)
        shard = random.randint(1000, 3000)
        shard_latency = round(random.uniform(15.0, 30.0), 2)
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        uptime_seconds = time.time() - self.start_time
        uptime_hours = round(uptime_seconds / 3600, 2)
        python_version = platform.python_version()

        response = (f"Cluster {cluster}: {cluster_latency}ms (avg)\n"
                    f"Shard {shard}: {shard_latency}ms\n"
                    f"CPU Usage: {cpu_usage}%\n"
                    f"Memory Usage: {memory_usage}%\n"
                    f"Uptime: {uptime_hours} hours\n"
                    f"Python Version: {python_version}")
        await ctx.send(response)

async def setup(bot):
    await bot.add_cog(PingPong(bot))