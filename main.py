import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import os
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Bot ready event
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# Slash command: Shadowban Checker
@bot.tree.command(name="shadowban", description="Check if an X account is shadowbanned")
async def shadowban(interaction: discord.Interaction, username: str):
    await interaction.response.defer()
    result = await check_shadowban(username)
    await interaction.followup.send(result)

# Slash command: Pick Reply
@bot.tree.command(name="pickreply", description="Pick a reply from an X post")
async def pickreply(interaction: discord.Interaction, post_url: str):
    await interaction.response.defer()
    result = await pick_reply(post_url)
    await interaction.followup.send(result)

# Function to check shadowban status
async def check_shadowban(username):
    url = f"https://shadowban.eu/.well-known/shadowban?screen_name={username}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                suspended = data.get('suspended')
                ghost_ban = data.get('ghost_ban')
                search_ban = data.get('search_ban')

                msg = f"**@{username} Shadowban Status:**\n"
                msg += f"Suspended: {'✅' if suspended else '❌'}\n"
                msg += f"Ghost Ban: {'✅' if ghost_ban else '❌'}\n"
                msg += f"Search Ban: {'✅' if search_ban else '❌'}\n"
                return msg
            else:
                return "Error fetching shadowban data."

# Function to pick a random reply
async def pick_reply(post_url):
    try:
        tweet_id = post_url.split('/')[-1]
        nitter_url = f"https://nitter.net/i/web/status/{tweet_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(nitter_url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                replies = soup.find_all("div", class_="reply")
                if not replies:
                    return "No replies found."

                reply_texts = [reply.text.strip() for reply in replies]
                picked = random.choice(reply_texts)
                return f"Random picked reply:\n{picked}"

    except Exception as e:
        return f"Error parsing the post: {str(e)}"

# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
