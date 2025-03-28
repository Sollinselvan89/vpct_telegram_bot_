import os
import logging
import time
from datetime import datetime
import schedule
from telegram import Bot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GROUP_CHAT_ID = os.getenv('TELEGRAM_GROUP_CHAT_ID')

# Initialize the bot
bot = Bot(token=TOKEN)

# Configure your reminders here
REMINDERS = {
    1: "🔔 Beginning of the month reminder: Time to review monthly goals!",
    5: "📝 5th day reminder: Weekly planning session today.",
    15: "📊 Mid-month reminder: Check progress on monthly tasks.",
    25: "🎯 End-of-month approaching: Prepare for next month's goals."
}

def send_reminder(message):
    """Send reminder message to the group"""
    try:
        bot.send_message(chat_id=GROUP_CHAT_ID, text=message)
        logger.info(f"Reminder sent: {message}")
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")

def check_reminders():
    """Check if today is a reminder day and send the appropriate message"""
    today = datetime.now().day
    if today in REMINDERS:
        send_reminder(REMINDERS[today])

def main():
    """Main function to run the bot"""
    logger.info("Starting Telegram Reminder Bot")
    
    # Print bot information
    bot_info = bot.get_me()
    logger.info(f"Bot started. Bot username: @{bot_info.username}")
    
    # Schedule the job to run daily at a specific time (e.g., 9:00 AM)
    schedule.every().day.at("09:00").do(check_reminders)
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()