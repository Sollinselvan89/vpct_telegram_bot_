# VPCT Telegram Reminder Bot

A simple Telegram bot that sends scheduled reminders to a group chat.

## Features

- Automated daily reminders based on the day of the month
- Customizable reminder messages
- Tag specific users in reminders
- Detailed logging for troubleshooting

## Setup

### Prerequisites

- Python 3.7+
- Telegram Bot Token (obtain from [@BotFather](https://t.me/botfather))
- Telegram Group Chat ID

### Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install python-telegram-bot
```

3. Set up environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your_token_here"
export TELEGRAM_GROUP_CHAT_ID="your_group_chat_id"
```

### Configuration

Edit the `REMINDERS` dictionary in `send_reminder.py` to customize your reminders:

```python
REMINDERS = {
    1: "🔔 @username1 Beginning of the month reminder: Time to review monthly goals!",
    5: "📝 @username2 5th day reminder: Weekly planning session today.",
    15: "📊 @username3 Mid-month reminder: Check progress on monthly tasks.",
    25: "🎯 @username4 End-of-month approaching: Prepare for next month's goals.",
    28: "🧪 Test message: This confirms the bot is working correctly!"
}
```

## Running Locally

```bash
python send_reminder.py
```

## GitHub Actions Deployment

This bot can be deployed using GitHub Actions to run automatically on a schedule:

1. Add repository secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_GROUP_CHAT_ID`

2. The included workflow file will run the bot daily at 8:00 UTC.

## Troubleshooting

Check the logs for errors. Common issues include:
- Incorrect bot token
- Invalid group chat ID
- Bot not added to the group chat
- Missing environment variables

## Future Roadmap

* Custom reminders via user commands
* Category tagging with hashtags
* Interactive buttons for reminder responses
* Advanced scheduling options (weekly, monthly)
* External service integrations
* User-specific personalization
* Analytics and reporting
* Multi-channel support
* File sharing capabilities
* Natural language processing

## License

[MIT](LICENSE)