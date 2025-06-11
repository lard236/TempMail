# Telegram Temp Mail Bot

A Telegram bot that generates temporary email addresses using mail.tm service. Built with aiogram 3.x.

## Features
- Generate temporary email addresses
- Receive and view incoming emails
- Modern inline keyboard interface
- Easy to use commands

## Setup
1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Create a `.env` file in the root directory with:
```
BOT_TOKEN=your_telegram_bot_token
```
4. Run the bot:
```bash
python bot.py
```

## Commands
- `/start` - Start the bot and see available commands
- `/newemail` - Generate a new temporary email
- `/check` - Check inbox for new messages
- `/help` - Show help message

## Note
This bot uses mail.tm service for temporary email generation. The service is free to use but may have limitations. 