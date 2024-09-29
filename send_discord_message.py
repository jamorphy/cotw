import discord
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

def send_message(message, channel_id):
    asyncio.run(send_discord_message(channel_id, message))

async def send_discord_message(channel_id, message):
    client = discord.Client(intents=discord.Intents.default())
    
    try:
        connection_task = asyncio.create_task(client.start(DISCORD_TOKEN))
        
        try:
            await asyncio.wait_for(client.wait_until_ready(), timeout=30.0)
        except asyncio.TimeoutError:
            print("Timeout: Failed to connect to Discord within 30 seconds.")
            return

        channel = client.get_channel(channel_id)
        if channel:
            await channel.send(message)
            print(f"Message sent successfully to channel {channel_id}")
        else:
            print(f"Channel with ID {channel_id} not found.")
    
    except discord.LoginFailure:
        print("Failed to log in: Invalid token")
    except Exception as e:
        print(f"An error occurred while sending the message: {e}")
    
    finally:
        await client.close()