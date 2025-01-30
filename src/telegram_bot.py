from telegram import Bot
from telegram.constants import ParseMode
import time
import os
import asyncio

# Replace with your bot token from BotFather
TOKEN = os.getenv('BOT_ID')
# Replace with your chat ID (you can get this by sending a message to your bot and checking the updates)
CHAT_ID = os.getenv('CHAT_ID')

# Initialize the bot
bot = Bot(token=TOKEN)

async def send_telegram_alert(message):
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=ParseMode.HTML)