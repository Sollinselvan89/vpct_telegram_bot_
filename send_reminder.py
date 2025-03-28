import os
import logging
from datetime import datetime
import telegram

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration from GitHub Secrets
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GROUP_CHAT_ID = os.environ.get('TELEGRAM_GROUP_CHAT_ID')

# Configure your reminders here
REMINDERS = {
    1: "🔔 Beginning of the month reminder: Time to review monthly goals!",
    5: "📝 5th day reminder: Weekly planning session today.",
    15: "📊 Mid-month reminder: Check progress on monthly tasks.",
    28: "🎯 End-of-month approaching: Prepare for next month's goals."
}

def send_reminder():
    """Check if today is a reminder day and send the appropriate message"""
    today = datetime.now().day
    
    if today not in REMINDERS:
        logger.info(f"No reminder scheduled for day {today}")
        return
    
    message = REMINDERS[today]
    logger.info(f"Sending reminder for day {today}: {message}")
    
try:
    bot = telegram.Bot(token=TOKEN)
    logger.info(f"Bot initialized with name: {bot.get_me().first_name}")
    logger.info(f"Attempting to send message to chat ID: {GROUP_CHAT_ID}")
    bot.send_message(chat_id=GROUP_CHAT_ID, text=message)
    logger.info("Reminder sent successfully")
except Exception as e:
    logger.error(f"Error sending reminder: {e}")
    logger.error(f"Error type: {type(e).__name__}")
    logger.error(f"Token length: {len(TOKEN) if TOKEN else 'Token is None'}")
    logger.error(f"Group ID: {GROUP_CHAT_ID}")
    raise

if __name__ == "__main__":
    logger.info("Starting Telegram Reminder Script")
    send_reminder()
    logger.info("Script execution completed")