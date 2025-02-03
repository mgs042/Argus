from telegram.constants import ParseMode
from config import check_telegram_status, get_telegram_details
import time
import os
import requests
from log import logger
# Replace with your bot token from BotFather
TOKEN = os.getenv('BOT_ID')
# Replace with your chat ID (you can get this by sending a message to your bot and checking the updates)
CHAT_ID = os.getenv('CHAT_ID')


def send_telegram_alert(name, eui, issue, message, severity, isGw=False):
    if isGw:
        alert = f'''🔴<b>Gateway Alert -- {issue}</b>
--------------------------------------------------------------
<b> Name:</b> {name}
<b> EUI:</b> {eui}
<b> Severity:</b> {severity}
--------------------------------------------------------------
<b> {issue}</b> - {message}
'''
    else:
        alert = f'''❗<b>Device Alert -- {issue}</b>
--------------------------------------------------------------
<b> Name:</b> {name}
<b> EUI:</b> {eui}
<b> Severity:</b> {severity}
--------------------------------------------------------------
<b> {issue}</b> - {message}
'''
    if TOKEN != '' and CHAT_ID != '':
        """Send a message to Telegram synchronously using the Telegram Bot API."""
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": alert,
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()  # Raise an error for bad status codes
            logger.info("Telegram Message sent successfully!")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
