import os
import logging
import sqlite3
from datetime import datetime, timedelta
from telegram.ext import Updater, CommandHandler
from flask import Flask
from threading import Thread
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

# --- Timezone ---
IST = pytz.timezone('Asia/Kolkata')


def get_current_ist():
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


# --- /start ---
def start(update, context):
    update.message.reply_text(
        "👋 Welcome! Use:\n"
        "/remindme YYYY-MM-DD HH:MM Message\n"
        "/repeatreminder daily|weekly|monthly HH:MM Message\n"
        "/listreminders\n"
        "/deletereminder <id>")


# --- /remindme ---
def remindme(update, context):
    try:
        if len(context.args) < 3:
            raise ValueError("Not enough arguments.")

        date_str = context.args[0]
        time_str = context.args[1]
        reminder_text = ' '.join(context.args[2:])

        remind_at = f"{date_str} {time_str}"
        scheduled_time = datetime.strptime(remind_at, '%Y-%m-%d %H:%M')

        now_ist = datetime.now(IST)
        if scheduled_time < now_ist:
            update.message.reply_text(
                "⏰ That time is in the past! Please pick a future time.")
            return

        conn = sqlite3.connect('reminders.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reminders (chat_id, reminder_text, remind_at) VALUES (?, ?, ?)",
            (update.message.chat_id, reminder_text, remind_at))
        conn.commit()
        conn.close()

        update.message.reply_text(f"✅ Reminder set for {remind_at} IST")
        logger.info(f"Reminder created: {remind_at} | {reminder_text}")
    except Exception as e:
        logger.error(f"❌ /remindme failed: {e}")
        update.message.reply_text(
            "❗ Usage: /remindme YYYY-MM-DD HH:MM Message\n"
            "Example: /remindme 2025-04-08 14:30 Call the doctor")


# --- /repeatreminder ---
def repeatreminder(update, context):
    try:
        recurrence = context.args[0].lower()
        if recurrence not in ['daily', 'weekly', 'monthly']:
            raise ValueError("Invalid recurrence")

        time_str = context.args[1]
        reminder_text = ' '.join(context.args[2:])
        today = datetime.now(IST).strftime('%Y-%m-%d')
        remind_at = f"{today} {time_str}"
        datetime.strptime(remind_at, '%Y-%m-%d %H:%M')

        conn = sqlite3.connect('reminders.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO recurring_reminders (chat_id, reminder_text, remind_at, recurrence) VALUES (?, ?, ?, ?)",
            (update.message.chat_id, reminder_text, remind_at, recurrence))
        conn.commit()
        conn.close()
        update.message.reply_text(
            f"🔁 Recurring reminder set: {recurrence} at {time_str} IST")
    except Exception as e:
        logger.error(f"❌ /repeatreminder failed: {e}")
        update.message.reply_text(
            "❗ Usage: /repeatreminder daily|weekly|monthly HH:MM Message\n"
            "Example: /repeatreminder daily 08:00 Drink water")


# --- /listreminders ---
def list_reminders(update, context):
    conn = sqlite3.connect('reminders.db')
    cursor = conn.cursor()
    msg = "📋 *One-Time Reminders:*\n"
    cursor.execute(
        "SELECT id, remind_at, reminder_text FROM reminders WHERE chat_id = ?",
        (update.message.chat_id, ))
    rows = cursor.fetchall()
    if rows:
        for id_, time_, text in rows:
            msg += f"🆔 {id_} | 🕒 {time_} | 📌 {text}\n"
    else:
        msg += "_None_\n"

    msg += "\n🔁 *Recurring Reminders:*\n"
    cursor.execute(
        "SELECT id, remind_at, reminder_text, recurrence FROM recurring_reminders WHERE chat_id = ?",
        (update.message.chat_id, ))
    rows = cursor.fetchall()
    if rows:
        for id_, time_, text, freq in rows:
            msg += f"🆔 {id_} | ⏰ {freq} | 🕒 {time_} | 📌 {text}\n"
    else:
        msg += "_None_"
    conn.close()
    update.message.reply_text(msg, parse_mode=telegram.ParseMode.MARKDOWN)


# --- /deletereminder ---
def delete_reminder(update, context):
    try:
        reminder_id = int(context.args[0])
        conn = sqlite3.connect('reminders.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ? AND chat_id = ?",
                       (reminder_id, update.message.chat_id))
        cursor.execute(
            "DELETE FROM recurring_reminders WHERE id = ? AND chat_id = ?",
            (reminder_id, update.message.chat_id))
        conn.commit()
        conn.close()
        update.message.reply_text(
            f"🗑️ Reminder ID {reminder_id} deleted (if it existed).")
    except Exception as e:
        logger.error(f"❌ /deletereminder failed: {e}")
        update.message.reply_text("❗ Usage: /deletereminder <reminder_id>")


# --- Reminder Checkers ---
def check_due_reminders(bot):
    now = get_current_ist()
    conn = sqlite3.connect('reminders.db')
    cursor = conn.cursor()

    # One-time
    cursor.execute(
        "SELECT id, chat_id, reminder_text FROM reminders WHERE remind_at <= ?",
        (now, ))
    for id_, chat_id, text in cursor.fetchall():
        bot.send_message(chat_id=chat_id, text=f"⏰ Reminder: {text}")
        cursor.execute("DELETE FROM reminders WHERE id = ?", (id_, ))

    # Recurring
    cursor.execute(
        "SELECT id, chat_id, reminder_text, remind_at, recurrence FROM recurring_reminders WHERE remind_at <= ?",
        (now, ))
    for id_, chat_id, text, time_str, freq in cursor.fetchall():
        bot.send_message(chat_id=chat_id, text=f"🔁 Reminder: {text}")
        next_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
        if freq == 'daily':
            next_time += timedelta(days=1)
        elif freq == 'weekly':
            next_time += timedelta(weeks=1)
        elif freq == 'monthly':
            month = next_time.month % 12 + 1
            year = next_time.year + (1 if month == 1 else 0)
            next_time = next_time.replace(year=year, month=month)
        cursor.execute(
            "UPDATE recurring_reminders SET remind_at = ? WHERE id = ?",
            (next_time.strftime('%Y-%m-%d %H:%M'), id_))
    conn.commit()
    conn.close()


# --- Monthly Reminder ---
def send_monthly_reminder(bot):
    today = datetime.now(IST).day
    if today in REMINDERS:
        bot.send_message(chat_id=GROUP_CHAT_ID, text=REMINDERS[today])


# --- Flask Keep-Alive ---
app = Flask('')


@app.route('/')
def home():
    return "I'm alive!"


def run_flask():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run_flask)
    t.start()


# --- Main ---
def main():
    setup_db()
    keep_alive()

    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("remindme", remindme))
    dp.add_handler(CommandHandler("repeatreminder", repeatreminder))
    dp.add_handler(CommandHandler("listreminders", list_reminders))
    dp.add_handler(CommandHandler("deletereminder", delete_reminder))

    send_monthly_reminder(updater.bot)
    check_due_reminders(updater.bot)

    updater.start_polling()
    logger.info("✅ Bot is running...")
    updater.idle()


if __name__ == '__main__':
    main()
