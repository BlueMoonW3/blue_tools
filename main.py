import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import os
import random
from dotenv import load_dotenv

# Load environment variables (for local testing)
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
    await interaction.followup.send("🔎 Checking shadowban status... (this may take a few seconds)")
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
    base_url = "https://x.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        # 1. Check if user exists
        profile_url = f"{base_url}/{username}"
        async with session.get(profile_url) as response:
            if response.status == 404:
                return f"❌ @{username} does not exist."

        # 2. Check Search Ban
        search_url = f"{base_url}/search?q=from%3A{username}&src=typed_query"
        async with session.get(search_url) as response:
            html = await response.text()
            if "No results for" in html or "Something went wrong" in html:
                search_ban = True
            else:
                search_ban = False

        # 3. Basic Thread Ban Detection
        async with session.get(profile_url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            tweet_links = []
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if f"/{username}/status/" in href and "/photo/" not in href:
                    tweet_links.append(href)

            if not tweet_links:
                return f"✅ @{username} exists.\n🚫 Unable to find tweets to check thread ban."

            # Pick the first tweet we find
            tweet_url = base_url + tweet_links[0]

        # Visit the tweet page
        async with session.get(tweet_url) as response:
            html = await response.text()

            if "This Tweet is unavailable" in html:
                thread_ban = True
            else:
                thread_ban = False

        # Final Result
        result = f"**Shadowban Check for @{username}:**\n"
        result += f"👤 User Exists: ✅\n"
        result += f"🔍 Search Ban: {'🚫 Yes' if search_ban else '✅ No'}\n"
        result += f"🧵 Thread Ban: {'🚫 Likely' if thread_ban else '✅ No evidence'}\n"

        return result

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
