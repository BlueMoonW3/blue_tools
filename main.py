import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Load environment variables
load_dotenv()

# Initialize bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Bot ready
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

# Shadowban checking function
async def check_shadowban(username):
    base_url = "https://x.com"
    search_url = f"{base_url}/search?q=from%3A{username}&src=typed_query"
    suggestion_url = f"{base_url}/search?q={username[:5]}&src=typed_query"

    result = {
        "account_exists": False,
        "suggestion_ban": None,
        "search_ban": None,
        "thread_ban": None,
        "reply_deboosting": None,
    }

    timeout = 15000  # 15 seconds max timeout for each page load

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 1. Check if account exists
            await page.goto(f"{base_url}/{username}", timeout=timeout)
            if "Sorry, that page doesn’t exist!" in await page.content():
                await browser.close()
                return f"❌ @{username} does not exist."
            else:
                result["account_exists"] = True

            # 2. Check Search Suggestion Ban
            await page.goto(suggestion_url, timeout=timeout)
            suggestion_html = await page.content()
            if f"@{username}" in suggestion_html:
                result["suggestion_ban"] = False
            else:
                result["suggestion_ban"] = True

            # 3. Check Search Ban
            await page.goto(search_url, timeout=timeout)
            search_html = await page.content()
            if "No results for" in search_html or "Something went wrong" in search_html:
                result["search_ban"] = True
            else:
                result["search_ban"] = False

            # 4. Check Ghost/Thread Ban
            await page.goto(f"{base_url}/{username}", timeout=timeout)
            tweets = await page.query_selector_all("article")
            if not tweets:
                result["thread_ban"] = True
            else:
                result["thread_ban"] = False

            # 5. Check Reply Deboosting (basic)
            if tweets:
                await tweets[0].click()
                await page.wait_for_timeout(2000)
                reply_page_html = await page.content()
                if "Show more replies" in reply_page_html:
                    result["reply_deboosting"] = True
                else:
                    result["reply_deboosting"] = False
            else:
                result["reply_deboosting"] = None  # Couldn't test

        except Exception as e:
            await browser.close()
            raise e

        await browser.close()

    # Build the output
    msg = f"🔎 **Shadowban Check for @{username}:**\n\n"
    msg += f"👤 Account Exists: ✅\n"
    msg += f"🔍 Search Suggestion Ban: {'🚫 Yes' if result['suggestion_ban'] else '✅ No'}\n"
    msg += f"🔎 Search Ban: {'🚫 Yes' if result['search_ban'] else '✅ No'}\n"
    msg += f"🧵 Ghost/Thread Ban: {'🚫 Yes' if result['thread_ban'] else '✅ No'}\n"
    if result["reply_deboosting"] is not None:
        msg += f"💬 Reply Deboosting: {'🚫 Yes' if result['reply_deboosting'] else '✅ No'}\n"
    else:
        msg += f"💬 Reply Deboosting: ⚠️ Could not test\n"

    return msg

# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
