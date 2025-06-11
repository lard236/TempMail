import os
import json
import logging
import aiohttp
import random
import string
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher()

# Constants
API_BASE_URL = "https://api.mail.tm"
DOMAINS_ENDPOINT = "/domains"
ACCOUNTS_ENDPOINT = "/accounts"
MESSAGES_ENDPOINT = "/messages"
TOKEN_ENDPOINT = "/token"

# Store user data (in memory - you might want to use a database in production)
user_data = {}

def generate_password(length=12):
    """Generate a random password."""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(characters) for _ in range(length))

async def get_domain():
    """Get available domain from mail.tm."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}{DOMAINS_ENDPOINT}") as response:
            domains = await response.json()
            return domains['hydra:member'][0]['domain']

async def create_email(domain: str):
    """Create a new email account."""
    email = f"{''.join(random.choices(string.ascii_lowercase + string.digits, k=10))}@{domain}"
    password = generate_password()
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_BASE_URL}{ACCOUNTS_ENDPOINT}",
            json={"address": email, "password": password}
        ) as response:
            if response.status == 201:
                # Get authentication token
                async with session.post(
                    f"{API_BASE_URL}{TOKEN_ENDPOINT}",
                    json={"address": email, "password": password}
                ) as token_response:
                    token_data = await token_response.json()
                    return {
                        "email": email,
                        "password": password,
                        "token": token_data.get("token")
                    }
    return None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handle /start command."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Generate New Email", callback_data="generate_email")],
        [InlineKeyboardButton(text="📨 Check Messages", callback_data="check_messages")],
        [InlineKeyboardButton(text="ℹ️ Help", callback_data="help")]
    ])
    
    await message.answer(
        "👋 Welcome to TempMail Bot!\n\n"
        "I can help you create temporary email addresses and manage incoming messages.\n\n"
        "Choose an action from the menu below:",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "generate_email")
async def generate_new_email(callback: types.CallbackQuery):
    """Generate a new temporary email address."""
    await callback.answer("⏳ Generating new email address...")
    
    try:
        domain = await get_domain()
        email_data = await create_email(domain)
        
        if email_data:
            user_data[callback.from_user.id] = email_data
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📨 Check Messages", callback_data="check_messages")],
                [InlineKeyboardButton(text="🔄 Generate New Email", callback_data="generate_email")]
            ])
            
            await callback.message.edit_text(
                f"✅ New email created successfully!\n\n"
                f"📧 Email: `{email_data['email']}`\n"
                f"🔑 Password: `{email_data['password']}`\n\n"
                f"_Click the button below to check messages_",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await callback.message.edit_text(
                "❌ Failed to create email address. Please try again.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Try Again", callback_data="generate_email")]
                ])
            )
    except Exception as e:
        logging.error(f"Error generating email: {e}")
        await callback.message.edit_text(
            "❌ An error occurred. Please try again later.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Try Again", callback_data="generate_email")]
            ])
        )

@dp.callback_query(F.data == "check_messages")
async def check_messages(callback: types.CallbackQuery):
    """Check messages for the current email address."""
    user_id = callback.from_user.id
    if user_id not in user_data:
        await callback.answer("❌ Please generate an email first!", show_alert=True)
        return

    await callback.answer("⏳ Checking messages...")
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {user_data[user_id]['token']}"}
            async with session.get(f"{API_BASE_URL}{MESSAGES_ENDPOINT}", headers=headers) as response:
                messages = await response.json()
                messages_list = messages.get('hydra:member', [])

                if not messages_list:
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Refresh", callback_data="check_messages")],
                        [InlineKeyboardButton(text="📧 Current Email", callback_data="show_email")]
                    ])
                    await callback.message.edit_text(
                        "📭 No messages yet!\n\n"
                        f"Email: `{user_data[user_id]['email']}`",
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                    return

                # Show latest 5 messages
                message_text = "📬 Latest messages:\n\n"
                for msg in messages_list[:5]:
                    from_name = msg['from']['name'] or 'Unknown'
                    subject = msg['subject'] or 'No subject'
                    intro = msg.get('intro', 'No preview available')
                    date = datetime.fromisoformat(msg['createdAt']).strftime('%Y-%m-%d %H:%M')
                    
                    message_text += (
                        f"📩 From: {from_name}\n"
                        f"📑 Subject: {subject}\n"
                        f"🕒 Date: {date}\n"
                        f"💬 Preview: {intro[:100]}...\n\n"
                    )

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Refresh", callback_data="check_messages")],
                    [InlineKeyboardButton(text="📧 Current Email", callback_data="show_email")]
                ])
                
                await callback.message.edit_text(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
    except Exception as e:
        logging.error(f"Error checking messages: {e}")
        await callback.message.edit_text(
            "❌ Error checking messages. Please try again.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Try Again", callback_data="check_messages")]
            ])
        )

@dp.callback_query(F.data == "show_email")
async def show_email(callback: types.CallbackQuery):
    """Show current email address."""
    user_id = callback.from_user.id
    if user_id not in user_data:
        await callback.answer("❌ No email generated yet!", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Check Messages", callback_data="check_messages")],
        [InlineKeyboardButton(text="🔄 Generate New Email", callback_data="generate_email")]
    ])
    
    await callback.message.edit_text(
        f"📧 Your current email:\n\n"
        f"Email: `{user_data[user_id]['email']}`\n"
        f"Password: `{user_data[user_id]['password']}`",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery):
    """Show help message."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="start")]
    ])
    
    help_text = (
        "📚 *How to use this bot:*\n\n"
        "1. Generate a new temporary email address\n"
        "2. Use this email address wherever you need\n"
        "3. Check for incoming messages\n"
        "4. Generate a new email address when needed\n\n"
        "*Available commands:*\n"
        "/start - Start the bot\n"
        "/newemail - Generate new email\n"
        "/check - Check messages\n"
        "/help - Show this help message"
    )
    
    await callback.message.edit_text(
        help_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "start")
async def return_to_start(callback: types.CallbackQuery):
    """Return to start menu."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Generate New Email", callback_data="generate_email")],
        [InlineKeyboardButton(text="📨 Check Messages", callback_data="check_messages")],
        [InlineKeyboardButton(text="ℹ️ Help", callback_data="help")]
    ])
    
    await callback.message.edit_text(
        "👋 Welcome to TempMail Bot!\n\n"
        "I can help you create temporary email addresses and manage incoming messages.\n\n"
        "Choose an action from the menu below:",
        reply_markup=keyboard
    )

async def main():
    """Start the bot."""
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main()) 