import discord
import asyncio

import os
from dotenv import load_dotenv

def send_video_complete_message(file_path):
    channel_id = 1283223113429024808
    message = f"Finished compiling video at: `{file_path}`"
    
    asyncio.run(send_discord_message(channel_id,  message))


async def send_discord_message(channel_id, message):
    client = discord.Client(intents=discord.Intents.default())
    
    @client.event
    async def on_ready():
        channel = client.get_channel(channel_id)
        if channel:
            await channel.send(message)
        else:
            print(f"Channel with ID {channel_id} not found.")
        await client.close()

    load_dotenv()

    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

    await client.start(DISCORD_TOKEN)