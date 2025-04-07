import os
import logging
import sqlite3
import time
import requests
import http.server
import socketserver
from threading import Thread
from datetime import datetime, timedelta
from telegram.ext import Updater, CommandHandler
import telegram
import pytz

# --- Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Environment Variables ---
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GROUP_CHAT_ID = os.environ.get('TELEGRAM_GROUP_CHAT_ID')
PORT = int(os.environ.get('PORT', 8080))  # Render assigns a PORT env var

# --- Timezone ---
IST = pytz.timezone('Asia/Kolkata')


def get_current_ist():
    """Get current time in IST timezone"""
    return datetime.now(IST).strftime('%Y-%m-%d %H:%M')


# --- Monthly Static Reminders ---
REMINDERS = {
    1: "🔔 Beginning of the month reminder: Time to review monthly goals!",
    5: "📝 5th day reminder: Weekly planning session today.",
    15: "📊 Mid-month reminder: Check progress on monthly tasks.",
    25: "🎯 End-of-month approaching: Prepare for next month's goals.",
}


# --- Database Setup ---
def setup_db():
    """Set up the SQLite database and tables"""
    conn = sqlite3.connect("reminders.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            reminder_text TEXT,
            remind_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recurring_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            reminder_text TEXT,
            remind_at TEXT,
            recurrence TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database setup complete")


# --- /start ---
def start(update, context):
    """Handle the /start command"""
    update.message.reply_text(
        "👋 Welcome! Use:\n"
        "/remindme YYYY-MM-DD HH:MM Message\n"
        "/repeatreminder daily|weekly|monthly HH:MM Message\n"
        "/listreminders\n"
        "/deletereminder <id>")


# --- /remindme ---
def remindme(update, context):
    """Handle the /remindme command"""
    try:
        if len(context.args) < 3:
            raise ValueError("Not enough arguments.")

        date_str = context.args[0]
        time_str = context.args[1]
        reminder_text = ' '.join(context.args[2:])

        # Validate date and time format
        remind_at = f"{date_str} {time_str}"
        try:
            scheduled_time = datetime.strptime(remind_at, '%Y-%m-%d %H:%M')
            
            # Convert to IST timezone for comparison
            scheduled_time_ist = IST.localize(scheduled_time) if scheduled_time.tzinfo is None else scheduled_time.astimezone(IST)
            now_ist = datetime.now(IST)
            
            if scheduled_time_ist < now_ist:
                update.message.reply_text(
                    "⏰ That time is in the past! Please pick a future time.")
                return
        except ValueError:
            update.message.reply_text("⚠️ Invalid date/time format. Use YYYY-MM-DD HH:MM")
            return

        # Store in database
        conn = sqlite3.connect('reminders.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reminders (chat_id, reminder_text, remind_at) VALUES (?, ?, ?)",
            (str(update.effective_chat.id), reminder_text, remind_at))
        conn.commit()
        reminder_id = cursor.lastrowid
        conn.close()

        update.message.reply_text(f"✅ Reminder #{reminder_id} set for {remind_at} IST")
        logger.info(f"Reminder created: {remind_at} | {reminder_text}")
    except Exception as e:
        logger.error(f"❌ /remindme failed: {str(e)}")
        update.message.reply_text(
            "❗ Usage: /remindme YYYY-MM-DD HH:MM Message\n"
            "Example: /remindme 2025-04-08 14:30 Call the doctor")


# --- /repeatreminder ---
def repeatreminder(update, context):
    """Handle the /repeatreminder command"""
    try:
        if len(context.args) < 3:
            raise ValueError("Not enough arguments.")
            
        recurrence = context.args[0].lower()
        if recurrence not in ['daily', 'weekly', 'monthly']:
            raise ValueError("Invalid recurrence")

        time_str = context.args[1]
        reminder_text = ' '.join(context.args[2:])
        
        # Validate time format
        try:
            time_obj = datetime.strptime(time_str, '%H:%M')
        except ValueError:
            update.message.reply_text("⚠️ Invalid time format. Use HH:MM (24-hour format)")
            return
            
        # Calculate the first occurrence time
        today = datetime.now(IST).strftime('%Y-%m-%d')
        remind_at = f"{today} {time_str}"
        
        # If the time is already past for today, schedule for tomorrow for daily reminders
        time_now = datetime.now(IST)
        scheduled_time = datetime.strptime(remind_at, '%Y-%m-%d %H:%M')
        scheduled_time_ist = IST.localize(scheduled_time) if scheduled_time.tzinfo is None else scheduled_time.astimezone(IST)
        
        if scheduled_time_ist < time_now and recurrence == 'daily':
            # Schedule for tomorrow
            tomorrow = (datetime.now(IST) + timedelta(days=1)).strftime('%Y-%m-%d')
            remind_at = f"{tomorrow} {time_str}"

        # Store in database
        conn = sqlite3.connect('reminders.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO recurring_reminders (chat_id, reminder_text, remind_at, recurrence) VALUES (?, ?, ?, ?)",
            (str(update.effective_chat.id), reminder_text, remind_at, recurrence))
        conn.commit()
        reminder_id = cursor.lastrowid
        conn.close()
        
        update.message.reply_text(
            f"🔁 Recurring reminder #{reminder_id} set: {recurrence} at {time_str} IST")
    except Exception as e:
        logger.error(f"❌ /repeatreminder failed: {str(e)}")
        update.message.reply_text(
            "❗ Usage: /repeatreminder daily|weekly|monthly HH:MM Message\n"
            "Example: /repeatreminder daily 08:00 Drink water")


# --- /listreminders ---
def list_reminders(update, context):
    """Handle the /listreminders command"""
    conn = sqlite3.connect('reminders.db')
    cursor = conn.cursor()
    msg = "📋 *One-Time Reminders:*\n"
    cursor.execute(
        "SELECT id, remind_at, reminder_text FROM reminders WHERE chat_id = ?",
        (str(update.effective_chat.id), ))
    rows = cursor.fetchall()
    if rows:
        for id_, time_, text in rows:
            msg += f"🆔 {id_} | 🕒 {time_} | 📌 {text}\n"
    else:
        msg += "_None_\n"

    msg += "\n🔁 *Recurring Reminders:*\n"
    cursor.execute(
        "SELECT id, remind_at, reminder_text, recurrence FROM recurring_reminders WHERE chat_id = ?",
        (str(update.effective_chat.id), ))
    rows = cursor.fetchall()
    if rows:
        for id_, time_, text, freq in rows:
            # Extract just the time part for display
            try:
                time_obj = datetime.strptime(time_, '%Y-%m-%d %H:%M')
                display_time = time_obj.strftime('%H:%M')
            except ValueError:
                display_time = time_
                
            msg += f"🆔 {id_} | ⏰ {freq} at {display_time} | 📌 {text}\n"
    else:
        msg += "_None_"
    conn.close()
    
    try:
        update.message.reply_text(msg, parse_mode=telegram.ParseMode.MARKDOWN)
    except telegram.error.BadRequest:
        # If markdown parsing fails, send without markdown
        update.message.reply_text("Failed to format message. Here's the plain text version:\n\n" + msg.replace('*', '').replace('_', ''))


# --- /deletereminder ---
def delete_reminder(update, context):
    """Handle the /deletereminder command"""
    try:
        if not context.args:
            raise ValueError("No reminder ID provided.")
            
        reminder_id = int(context.args[0])
        conn = sqlite3.connect('reminders.db')
        cursor = conn.cursor()
        
        # Check if the reminder exists and belongs to this user
        cursor.execute("SELECT id FROM reminders WHERE id = ? AND chat_id = ?",
                      (reminder_id, str(update.effective_chat.id)))
        one_time = cursor.fetchone()
                       
        cursor.execute("SELECT id FROM recurring_reminders WHERE id = ? AND chat_id = ?",
                      (reminder_id, str(update.effective_chat.id)))
        recurring = cursor.fetchone()
        
        if not one_time and not recurring:
            update.message.reply_text(f"⚠️ No reminder with ID {reminder_id} found.")
            conn.close()
            return
            
        # Delete the reminder
        cursor.execute("DELETE FROM reminders WHERE id = ? AND chat_id = ?",
                       (reminder_id, str(update.effective_chat.id)))
                       
        cursor.execute(
            "DELETE FROM recurring_reminders WHERE id = ? AND chat_id = ?",
            (reminder_id, str(update.effective_chat.id)))
            
        conn.commit()
        conn.close()
        update.message.reply_text(
            f"🗑️ Reminder ID {reminder_id} deleted successfully.")
    except ValueError:
        logger.error("❌ /deletereminder failed: No reminder ID provided")
        update.message.reply_text("❗ Usage: /deletereminder <reminder_id>")
    except Exception as e:
        logger.error(f"❌ /deletereminder failed: {str(e)}")
        update.message.reply_text("❗ Usage: /deletereminder <reminder_id>")


# --- Reminder Checkers ---
def check_due_reminders(bot):
    """Check for due reminders and send notifications"""
    now = get_current_ist()
    now_dt = datetime.strptime(now, '%Y-%m-%d %H:%M')
    conn = sqlite3.connect('reminders.db')
    cursor = conn.cursor()

    # One-time reminders
    cursor.execute(
        "SELECT id, chat_id, reminder_text, remind_at FROM reminders")
    for id_, chat_id, text, remind_at in cursor.fetchall():
        try:
            remind_dt = datetime.strptime(remind_at, '%Y-%m-%d %H:%M')
            if remind_dt <= now_dt:
                try:
                    bot.send_message(chat_id=chat_id, text=f"⏰ Reminder: {text}")
                    logger.info(f"Sent one-time reminder {id_} to {chat_id}")
                    cursor.execute("DELETE FROM reminders WHERE id = ?", (id_,))
                except Exception as e:
                    logger.error(f"Failed to send reminder {id_}: {str(e)}")
        except ValueError:
            logger.error(f"Invalid date format for reminder {id_}: {remind_at}")
            continue

    # Recurring reminders
    cursor.execute(
        "SELECT id, chat_id, reminder_text, remind_at, recurrence FROM recurring_reminders")
    for id_, chat_id, text, remind_at, freq in cursor.fetchall():
        try:
            remind_dt = datetime.strptime(remind_at, '%Y-%m-%d %H:%M')
            if remind_dt <= now_dt:
                try:
                    bot.send_message(chat_id=chat_id, text=f"🔁 Recurring Reminder: {text}")
                    logger.info(f"Sent recurring reminder {id_} to {chat_id}")
                    
                    # Calculate next occurrence time
                    if freq == 'daily':
                        next_time = remind_dt + timedelta(days=1)
                    elif freq == 'weekly':
                        next_time = remind_dt + timedelta(weeks=1)
                    elif freq == 'monthly':
                        # Handle month rollover
                        month = remind_dt.month % 12 + 1
                        year = remind_dt.year + (1 if month == 1 else 0)
                        try:
                            next_time = remind_dt.replace(year=year, month=month)
                        except ValueError:  # Handle case where the day doesn't exist in the next month
                            # Get the last day of the next month
                            if month == 2:  # February
                                last_day = 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28
                            elif month in [4, 6, 9, 11]:  # 30-day months
                                last_day = 30
                            else:  # 31-day months
                                last_day = 31
                            next_time = remind_dt.replace(year=year, month=month, day=last_day)
                    
                    cursor.execute(
                        "UPDATE recurring_reminders SET remind_at = ? WHERE id = ?",
                        (next_time.strftime('%Y-%m-%d %H:%M'), id_))
                except Exception as e:
                    logger.error(f"Failed to send recurring reminder {id_}: {str(e)}")
        except ValueError:
            logger.error(f"Invalid date format for recurring reminder {id_}: {remind_at}")
            continue
            
    conn.commit()
    conn.close()


# --- Monthly Reminder ---
def send_monthly_reminder(bot):
    """Send monthly reminders to the group chat"""
    if not GROUP_CHAT_ID:
        logger.warning("GROUP_CHAT_ID not set, skipping monthly reminders")
        return
        
    today = datetime.now(IST).day
    if today in REMINDERS:
        try:
            bot.send_message(chat_id=GROUP_CHAT_ID, text=REMINDERS[today])
            logger.info(f"Sent monthly reminder for day {today}")
        except Exception as e:
            logger.error(f"Failed to send monthly reminder: {str(e)}")


# --- Simple HTTP Server for Render ---
class SimpleHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Telegram Reminder Bot is running!')
        
    def log_message(self, format, *args):
        # Suppress logging of HTTP requests
        return


def run_http_server():
    """Run a simple HTTP server to satisfy Render's port binding requirement"""
    handler = SimpleHTTPHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        logger.info(f"HTTP server running on port {PORT}")
        httpd.serve_forever()


# --- Main ---
def main():
    """Main function to run the bot"""
    setup_db()
    
    # Start HTTP server in a separate thread for Render
    server_thread = Thread(target=run_http_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Initialize the bot
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    # Add command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("remindme", remindme))
    dp.add_handler(CommandHandler("repeatreminder", repeatreminder))
    dp.add_handler(CommandHandler("listreminders", list_reminders))
    dp.add_handler(CommandHandler("deletereminder", delete_reminder))

    # Start the bot
    updater.start_polling()
    logger.info("✅ Bot is running...")
    
    # Run the first checks
    send_monthly_reminder(updater.bot)
    check_due_reminders(updater.bot)
    
    # Main loop for checks
    try:
        while True:
            time.sleep(60)  # Check every minute
            check_due_reminders(updater.bot)
                
            # Check for monthly reminders once per day
            if datetime.now(IST).hour == 8 and datetime.now(IST).minute == 0:
                send_monthly_reminder(updater.bot)
    except KeyboardInterrupt:
        updater.stop()
        logger.info("Bot stopped")


if __name__ == '__main__':
    main()
