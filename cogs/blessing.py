import discord
from discord import app_commands
from discord.ext import commands

class BlessingCalculator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Sync the command tree when the bot is ready
        await self.bot.tree.sync()
        print("BlessingCalculator commands synced successfully.")

    @app_commands.command(name="blessing", description="Calculate if it's better to buy blue or purple blessings.")
    async def blessing(self, interaction: discord.Interaction, blue_cost: int, purple_cost: int):
        # Constants from the provided image
        base_chance = {
            "green_on_blue": 0.10,
            "blue_on_purple": 0.10,
            "green_on_purple": 0.01
        }
        blessing_needed = {
            "green_on_blue": 90,
            "blue_on_purple": 450,
            "green_on_purple": 990
        }
        blessing_gained = {
            "green_on_blue": 8,
            "blue_on_purple": 40,
            "green_on_purple": 8
        }
        
        # Calculate number of blessings required to guarantee success
        fails_needed = {
            key: blessing_needed[key] / blessing_gained[key] for key in blessing_needed
        }
        
        # Calculate cost to reach 100% for blue (for purple it's a fixed cost)
        blue_total_cost = blue_cost * fails_needed["green_on_blue"]
        purple_total_cost = purple_cost  # Only one purple needed to reach 100%
        
        # Additional calculations for partial blessings
        partial_blessings = {
            "50%": 0.5 * blessing_needed["green_on_blue"],
            "70%": 0.7 * blessing_needed["green_on_blue"],
            "80%": 0.8 * blessing_needed["green_on_blue"]
        }
        partial_costs = {key: (value / blessing_gained["green_on_blue"]) * blue_cost for key, value in partial_blessings.items()}
        
        # Calculate potential savings if gambling at different thresholds
        savings = {key: purple_total_cost - cost for key, cost in partial_costs.items()}
        
        # Create an embed response
        embed = discord.Embed(title="🎲 Blessing Cost Analysis 🎲", color=discord.Color.blue())
        embed.set_thumbnail(url="https://haruki.s-ul.eu/fjEy0RW7")
        
        if blue_total_cost < purple_total_cost:
            embed.add_field(name="✅ Cost-effective Option", value="It is more cost-effective to buy **Blue blessings**.", inline=False)
        else:
            embed.add_field(name="✅ Cost-effective Option", value="It is more cost-effective to buy **Purple blessings**.", inline=False)
        
        embed.add_field(name="💙 Total Cost for Blue Blessings", value=f"`{blue_total_cost:.2f} Luscent`", inline=False)
        embed.add_field(name="💜 Total Cost for Purple Blessings", value=f"`{purple_total_cost:.2f} Luscent`", inline=False)
        
        # Add partial blessing information
        embed.add_field(name="🔮 Partial Blessing Gamble Options", value="Below are options for partial blessings:", inline=False)
        for key, value in partial_costs.items():
            bar_length = int((float(key.strip('%')) / 100) * 20)
            bar = "{}{}".format("\u2588" * bar_length, "\u2591" * (20 - bar_length))
            embed.add_field(
                name=f"{key} Chance",
                value=f"{bar} `{value:.2f} Luscent` (💰 **Savings**: `{savings[key]:.2f} Luscent`)",
                inline=False
            )
        
        embed.set_footer(text="💡 Note: Gambling with partial blessings might save you Luscent but comes with a risk of failure.")
        
        # Send the response
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(BlessingCalculator(bot))
