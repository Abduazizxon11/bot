# Telegram Bot

A Telegram bot built with Python that handles user registration and manages subscriptions.

## Requirements

- Python 3.8+
- PostgreSQL database (provided by Railway)
- Telegram Bot Token

## Environment Variables

The following environment variables need to be set:

- `BOT_TOKEN`: Your Telegram Bot Token
- `DATABASE_URL`: PostgreSQL connection URL (automatically set by Railway)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the bot:
```bash
python bot.py 