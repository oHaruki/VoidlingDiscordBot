import discord
from discord.ext import commands
from collections import defaultdict

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store item reactions
item_reactions = defaultdict(list)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command(name="post_drops")
async def post_drops(ctx, *items):
    # Check if the number of items is exactly 7
    if len(items) != 7:
        await ctx.send("Please provide exactly 7 items for the drop list.")
        return

    # Create embed message for items
    embed = discord.Embed(
        title="Weekly Guild Boss Drops",
        description="React to the items you need!",
        color=discord.Color.blue()
    )

    # Adding fields for each item
    for i, item in enumerate(items, 1):
        embed.add_field(name=f"Item {i}", value=item, inline=False)

    # Send the embed message
    message = await ctx.send(embed=embed)

    # Adding reactions (use emoji numbers 1-7)
    emoji_numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣']
    for emoji in emoji_numbers:
        await message.add_reaction(emoji)

    # Storing message ID and reactions for reference
    item_reactions[message.id] = list(items)

@bot.command(name="get_votes")
async def get_votes(ctx, message_id: int):
    # Retrieve the message based on ID
    try:
        message = await ctx.fetch_message(message_id)
    except discord.NotFound:
        await ctx.send("Message not found. Please make sure the ID is correct.")
        return

    # Collect reactions and users
    results = defaultdict(list)
    for reaction in message.reactions:
        if reaction.emoji in ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣']:
            users = await reaction.users().flatten()
            item_index = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣'].index(reaction.emoji)
            for user in users:
                if user != bot.user:  # Exclude the bot itself
                    results[item_reactions[message.id][item_index]].append(user.name)

    # Format results
    results_text = "\n".join([f"{item}: {', '.join(users)}" for item, users in results.items()])
    await ctx.send(f"Reaction results:\n{results_text if results_text else 'No votes yet!'}")

bot.run("YOUR_DISCORD_BOT_TOKEN")
