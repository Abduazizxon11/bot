import telebot
from telebot import types
import psycopg2
import os
from flask import Flask, request
import threading
from urllib.parse import urlparse
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Telegram Bot Token
TOKEN = "7589416221:AAG0XhJZ1U3y-0IH8RH2z8Vih5uvyE47nTQ"
logger.info(f"Bot token loaded: {TOKEN[:5]}...")

bot = telebot.TeleBot(TOKEN)

# Database Connection (PostgreSQL)
DATABASE_URL = "postgresql://postgres:tiSCQbRJGwDlDMiTyBqpwGxUcLLfkgjY@postgres.railway.internal:5432/railway"
logger.info(f"Database URL loaded: {DATABASE_URL[:20]}...")

# Admins & Channel
ADMINS = [1547087017, 1154080413, 1071518993]
CHAT_ID = -1002433031538
CHANNEL_USE = "@socraticquiz"
MAX_USERS = 150

# Flask App for Webhooks
app = Flask(__name__)

# Webhook settings
WEBHOOK_HOST = "https://bot-production-f3b4.up.railway.app"
logger.info(f"Webhook host: {WEBHOOK_HOST}")

# Database Functions
def connect_db():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def create_db():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE,
            phone VARCHAR(13),
            name VARCHAR(50),
            age INTEGER,
            username VARCHAR(30)
        )''')
    conn.commit()
    conn.close()

create_db()

def get_user(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def save_user(user_id, phone, name, age, username):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, phone, name, age, username) VALUES (%s, %s, %s, %s, %s)",
                   (user_id, phone, name, age, username))
    conn.commit()
    conn.close()

def count_user():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USE, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
        return False

@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        bot.process_new_updates([telebot.types.Update.de_json(update)])
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

@bot.message_handler(commands=['start'])
def greeting(message):
    user_id = message.chat.id
    if not is_subscribed(user_id):
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("🔔 Subscribe", url=f"https://t.me/{CHANNEL_USE[1:]}")
        keyboard.add(button)
        bot.send_message(user_id, "❗️ Please, subscribe to our channel to use bot.", reply_markup=keyboard)
        return

    keyboard = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("🏃‍♂️‍➡️ Start your journey", callback_data="starting")
    keyboard.add(button)
    bot.send_message(user_id, "Welcome to Socratic Community!", reply_markup=keyboard)

@bot.message_handler(commands=['register'])
def registering(message):
    user_id = message.chat.id
    if not is_subscribed(user_id):
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("🔔 Subscribe", url=f"https://t.me/{CHANNEL_USE[1:]}")
        keyboard.add(button)
        bot.send_message(user_id, "❗️ To use the bot, please subscribe to our channel.", reply_markup=keyboard)
        return

    if get_user(user_id):
        bot.send_message(user_id, "You are already registered!")
        return

    if count_user() >= MAX_USERS:
        bot.send_message(user_id, "❌ Sorry, the registration limit has been reached.")
        return

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📱 Share phone number", request_contact=True)
    keyboard.add(button)
    bot.send_message(user_id, "Press the button below to share your number", reply_markup=keyboard)

@bot.message_handler(content_types=['contact'])
def get_contact(message):
    user_id = message.chat.id
    phone = message.contact.phone_number
    bot.send_message(user_id, "Thanks! Now we need your name (only name)")
    bot.register_next_step_handler(message, ask_name, user_id, phone)

def ask_name(message, user_id, phone):
    name = message.text.strip()
    if not name.isalpha():
        bot.send_message(user_id, "Error! Please enter a valid name:")
        bot.register_next_step_handler(message, ask_name, user_id, phone)
        return
    bot.send_message(user_id, "Now write your age")
    bot.register_next_step_handler(message, ask_age, user_id, phone, name)

def ask_age(message, user_id, phone, name):
    try:
        age = int(message.text)
        if age < 15 or age > 19:
            bot.send_message(user_id, "Sorry, you are not eligible for this event.")
            return
        save_user(user_id, phone, name, age, message.from_user.username or "No username")
        bot.send_message(user_id, "🎉 Registration successful! Wait for admin approval.")
    except ValueError:
        bot.send_message(user_id, "Error! Please enter a valid age:")
        bot.register_next_step_handler(message, ask_age, user_id, phone, name)

# Webhook settings
WEBHOOK_PATH = f'/webhook/{TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

@app.route('/webhook_info')
def webhook_info():
    try:
        info = bot.get_webhook_info()
        return {
            "url": info.url,
            "has_custom_certificate": info.has_custom_certificate,
            "pending_update_count": info.pending_update_count,
            "last_error_date": info.last_error_date,
            "last_error_message": info.last_error_message,
            "max_connections": info.max_connections,
            "ip_address": info.ip_address
        }
    except Exception as e:
        logger.error(f"Webhook info error: {e}")
        return {"error": str(e)}, 500

def setup_webhook():
    try:
        logger.info("Removing old webhook...")
        bot.remove_webhook()
        logger.info(f"Setting new webhook to {WEBHOOK_URL}")
        bot.set_webhook(url=WEBHOOK_URL)
        logger.info("Webhook setup completed successfully")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        raise

# Add callback handler for the "starting" button
@bot.callback_query_handler(func=lambda call: call.data == "starting")
def callback_starting(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "Great! Use /register command to start registration process.")

if __name__ == "__main__":
    try:
        # Setup webhook
        setup_webhook()
        # Start Flask server
        port = int(os.getenv('PORT', 8080))  # Railway often uses port 8080
        logger.info(f"Starting server on port {port}")
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Application startup error: {e}")
        raise
