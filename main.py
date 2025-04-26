import discord
from discord.ext import commands
import httpx
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
    await interaction.response.defer(thinking=True)
    try:
        result = await check_shadowban(username)
    except Exception as e:
        result = f"⚠️ Error checking shadowban: {str(e)}"
    await interaction.followup.send(content=result)

# Slash command: Pick Reply
@bot.tree.command(name="pickreply", description="Pick a reply from an X post")
async def pickreply(interaction: discord.Interaction, post_url: str):
    await interaction.response.defer(thinking=True)
    try:
        result = await pick_reply(post_url)
    except Exception as e:
        result = f"⚠️ Error picking a reply: {str(e)}"
    await interaction.followup.send(content=result)

# Shadowban checking function
async def check_shadowban(username):
    base_url = "https://x.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
    }
    timeout = httpx.Timeout(10.0)

    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        # 1. Check if user exists
        profile_url = f"{base_url}/{username}"
        response = await client.get(profile_url)
        if response.status_code == 404:
            return f"❌ @{username} does not exist."
        if response.status_code != 200:
            return f"⚠️ Couldn't verify user existence (Status code {response.status_code})."

        # 2. Search Suggestion Ban Check
        partial_name = username[:6]  # take first few letters
        suggestion_url = f"{base_url}/search?q={partial_name}&src=typed_query"
        response = await client.get(suggestion_url)
        html = response.text
        if f"@{username}" in html:
            suggestion_ban = False
        else:
            suggestion_ban = True

        # 3. Search Ban Check
        search_url = f"{base_url}/search?q=from%3A{username}&src=typed_query"
        response = await client.get(search_url)
        html = response.text
        if "No results for" in html or "Something went wrong" in html:
            search_ban = True
        else:
            search_ban = False

        # 4. Ghost/Thread Ban Check
        response = await client.get(profile_url)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        tweet_links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if f"/{username}/status/" in href and "/photo/" not in href:
                tweet_links.append(href)

        if not tweet_links:
            thread_ban_result = "🚫 Unable to find tweets to check thread ban."
            thread_ban = True
        else:
            tweet_url = base_url + tweet_links[0]
            response = await client.get(tweet_url)
            tweet_html = response.text

            if "This Tweet is unavailable" in tweet_html:
                thread_ban = True
            else:
                thread_ban = False

        # 5. Reply Deboosting Check (basic version)
        if tweet_links:
            reply_page_url = base_url + tweet_links[0]
            response = await client.get(reply_page_url)
            reply_html = response.text
            if "Show more replies" in reply_html:
                reply_deboosting = True
            else:
                reply_deboosting = False
        else:
            reply_deboosting = True  # If no tweets, assume risky

    # Assemble full result
    result = (
        f"🔎 **Shadowban Check for @{username}:**\n\n"
        f"👤 Account Exists: ✅\n"
        f"🔍 Search Suggestion Ban: {'🚫 Yes' if suggestion_ban else '✅ No'}\n"
        f"🔎 Search Ban: {'🚫 Yes' if search_ban else '✅ No'}\n"
        f"🧵 Ghost/Thread Ban: {'🚫 Yes' if thread_ban else '✅ No'}\n"
        f"💬 Reply Deboosting: {'🚫 Yes' if reply_deboosting else '✅ No'}\n"
    )
    return result

# Pick a random reply function
async def pick_reply(post_url):
    tweet_id = post_url.split('/')[-1]
    nitter_url = f"https://nitter.net/i/web/status/{tweet_id}"

    timeout = httpx.Timeout(10.0)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(nitter_url)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        replies = soup.find_all("div", class_="reply")
        if not replies:
            return "No replies found."

        reply_texts = [reply.text.strip() for reply in replies]
        picked = random.choice(reply_texts)
        return f"🎯 Random picked reply:\n\n{picked}"

# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
