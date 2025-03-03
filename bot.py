import telebot
from telebot import types
import psycopg2
import os
from flask import Flask, request
import threading

# Telegram Bot Token
TOKEN = os.getenv('7589416221:AAG0XhJZ1U3y-0IH8RH2z8Vih5uvyE47nTQ')
bot = telebot.TeleBot(TOKEN)

# Database Connection (PostgreSQL)
DB_NAME = "smth_bot_db"
DB_USER = "postgres"
DB_PASSWORD = "root"
DB_HOST = "localhost"
DB_PORT = "5432"

# Admins & Channel
ADMINS = [1547087017, 1154080413, 1071518993]
CHAT_ID = -1002433031538
CHANNEL_USE = "@socraticquiz"
MAX_USERS = 75

# Flask App for Webhooks
app = Flask(__name__)

# Database Functions
def connect_db():
    return psycopg2.connect(database=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)

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

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    bot.process_new_updates([telebot.types.Update.de_json(update)])
    return "OK", 200

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

# Webhook Setup (Moved to Global Level)
bot.remove_webhook()
bot.set_webhook(url=f"https://yourdomain.com/{TOKEN}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
