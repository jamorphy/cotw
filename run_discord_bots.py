import discord
from discord.ext import commands
import asyncio

import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

CHANNEL_ID = 1283223113429024808  # Replace with your actual channel ID

# Set up the bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        print(f"Connected to channel: {channel.name}")
    else:
        print(f"Could not find channel with ID {CHANNEL_ID}")
# Run the bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)