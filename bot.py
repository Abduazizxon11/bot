import telebot
from telebot import types
import psycopg2
from dotenv import load_dotenv
import os
import time

load_dotenv()

# Проверяем, что все переменные заданы
REQUIRED_ENV_VARS = ["Bot_token", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"]
for var in REQUIRED_ENV_VARS:
    if not os.getenv(var):
        raise ValueError(f"❌ ERROR: {var} is not set in .env file!")

# Настройки
bot = telebot.TeleBot(os.getenv("Bot_token"))
chat = -1002433031538
ADMINS = [1547087017, 1154080413, 1071518993]
channel = "@socraticquiz"
max_user = 500
user_message = {}

# Подключение к БД
def connect_db():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

# Создание таблицы
def create_db():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        user_id BIGINT UNIQUE,
        phone TEXT,
        name TEXT,
        age INTEGER,
        username TEXT
    )
    """)
    conn.commit()
    cursor.close()
    conn.close()

create_db()

# Получение пользователя
def get_user(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

# Сохранение пользователя
def save_user(user_id, phone, name, age, username):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, phone, name, age, username) VALUES (%s, %s, %s, %s, %s)",
                   (user_id, phone, name, age, username))
    conn.commit()
    cursor.close()
    conn.close()

# Подсчёт пользователей
def count_user():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count

# Проверка подписки
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(channel, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception:
        return False

# Команда /send (для админов)
@bot.message_handler(commands=["send"])
def send(message):
    if message.chat.id not in ADMINS:
        bot.send_message(message.chat.id, "❌ You are not authorized to use this command.")
        return

    try:
        args = message.text.split(' ', 2)
        if len(args) < 3:
            bot.send_message(message.chat.id, "⚠️ Usage: /send <user_id> <message>")
            return
        user_id = int(args[1])
        user_rot = args[2]
        bot.send_message(user_id, f"📩 Message from admin:\n\n{user_rot}")
        bot.send_message(message.chat.id, "✅ Message sent successfully!")
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ Invalid user ID.")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error sending message: {e}")

# Команда /start
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id

    if not is_subscribed(user_id):
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("🔔 Subscribe", url=f"https://t.me/{channel[1:]}")
        keyboard.add(button)
        bot.send_message(user_id, "❗ Please, subscribe to our channel to use bot.", reply_markup=keyboard)
        return

    with open("smaller_image.png", "rb") as photo:
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("🏃‍♂️‍➡️ Start your journey", callback_data="starting")
        keyboard.add(button)
        bot.send_photo(user_id, photo, caption=f"Dear {message.from_user.first_name}\n\n"
                                               f"<b>Welcome to Socratic Community!\n\nAt Socratic Community, we believe that every great idea starts with a question.\nOur team is a collective of thinkers, dreamers, and innovators who engage in deep discussions, challenge perspectives, and seek truth through open dialogue. Join us in the pursuit of wisdom!</b>",
                       parse_mode="html", reply_markup=keyboard)

# Команда /help
@bot.message_handler(commands=["help"])
def hela(message):
    user_id = message.chat.id

    if not is_subscribed(user_id):
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("🔔 Subscribe", url=f"https://t.me/{channel[1:]}")
        keyboard.add(button)
        bot.send_message(user_id, "❗ To use the bot, please subscribe to our channel.", reply_markup=keyboard)
        return

    bot.send_message(message.chat.id, "<b>Here is the list of commands:</b>\n\n"
                                      "/register - <b>start the registration process</b>\n"
                                      "/problem - <b>if you have problems with bot</b>\n"
                                      "/help - <b>show all available commands</b>", parse_mode="html")

# Команда /register
@bot.message_handler(commands=['register'])
def registering(message):
    user_id = message.chat.id
    if not is_subscribed(user_id):
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("🔔 Subscribe", url=f"https://t.me/{channel[1:]}")
        keyboard.add(button)
        bot.send_message(user_id, "❗ To use the bot, please subscribe to our channel.", reply_markup=keyboard)
        return

    if get_user(user_id):
        bot.send_message(message.chat.id, "You are already registered!")
        return

    if count_user() >= max_user:
        bot.send_message(message.chat.id, "❌ Sorry, the registration limit has been reached.")
        return

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📱 Share phone number", request_contact=True)
    keyboard.add(button)
    bot.send_message(message.chat.id, "Press the button below to share your number", reply_markup=keyboard)

@bot.message_handler(content_types=['contact'])
def get_contact(message):
    user_id = message.chat.id
    contact = message.contact
    phone = contact.phone_number

    remove_keyboard = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Thanks! Now we need your name (only name)", reply_markup=remove_keyboard)
    bot.register_next_step_handler(message, ask_name, user_id, phone)

def ask_name(message, user_id, phone):
    name = message.text.strip()

    if not name.isalpha() or len(name) < 2:
        bot.send_message(message.chat.id, "Error!\nPlease write your name:")
        bot.register_next_step_handler(message, ask_name, user_id, phone)
        return

    bot.send_message(message.chat.id, "Now write your age")
    bot.register_next_step_handler(message, ask_age, user_id, phone, name)

def ask_age(message, user_id, phone, name):
    try:
        age = int(message.text)
        if age < 15 or age > 19:
            bot.send_message(message.chat.id, "Sorry, but you are too young/old for this event.")
            bot.register_next_step_handler(message, ask_age, user_id, phone, name)
            return

        confirm_data(message, user_id, phone, name, age)
    except ValueError:
        bot.send_message(message.chat.id, "Error!\nPlease write your age as a number:")
        bot.register_next_step_handler(message, ask_age, user_id, phone, name)

def confirm_data(message, user_id, phone, name, age):
    username = message.from_user.username or "No username"
    save_user(user_id, phone, name, age, username)

    user_text = (
        f"✅ New user registered!\n\n"
        f"📞 Phone number: {phone}\n"
        f"👤 Name: {name}\n"
        f"🎂 Age: {age} years old\n"
        f"💬 Username: @{username}\n"
        f"🆔 ID: {user_id}"
    )

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("✅ Accept", callback_data=f'good_{user_id}'),
        types.InlineKeyboardButton("❌ Decline", callback_data=f'bad_{user_id}')
    )

    sent_message = bot.send_message(message.chat.id, "🎉 Thanks!\n\nWait until your registration is reviewed")
    user_message[user_id] = sent_message.message_id
    bot.send_message(chat, user_text, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('good_'))
def accept_user(call):
    user_id = int(call.data.split('_')[1])
    if user_id in user_message:
        try:
            bot.delete_message(user_id, user_message[user_id])
        except:
            pass
        del user_message[user_id]

    with open("reg.png", "rb") as photo:
        bot.send_photo(user_id, photo, caption="✅ Congratulations! Your registration has been accepted. Welcome to Socratic Community! 🎉")

    bot.send_location(user_id, 41.308228, 69.244500)
    bot.send_message(user_id, "Location: SATASHKENT\nTime: 1 p.m")
    bot.send_message(user_id, f"Your verified key {call.from_user.id}")

    try:
        new_text = call.message.text + "\n\n✅ Accepted"
        bot.edit_message_text(new_text, chat_id=call.message.chat.id, message_id=call.message.message_id)
    except:
        pass

    bot.answer_callback_query(call.id, "User accepted!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('bad_'))
def decline_user(call):
    user_id = int(call.data.split('_')[1])
    if user_id in user_message:
        try:
            bot.delete_message(user_id, user_message[user_id])
        except:
            pass
        del user_message[user_id]

    bot.send_message(user_id, "❌ Sorry! Your registration has been declined.")

    try:
        new_text = call.message.text + "\n\n❌ Declined"
        bot.edit_message_text(new_text, chat_id=call.message.chat.id, message_id=call.message.message_id)
    except:
        pass

    bot.answer_callback_query(call.id, "User declined!")

@bot.callback_query_handler(func=lambda call: call.data == "starting")
def start2(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    hela(call.message)

@bot.message_handler(commands=['problem'])
def problem(message):
    keyboard = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("💬 Bot manager", url="https://t.me/Ooooooooooooo0oooooooooooooooooo")
    keyboard.add(button)
    bot.reply_to(message, "Ask our bot manager if you have any technical issues with the bot:", reply_markup=keyboard)

# Запуск
if __name__ == "__main__":
    while True:
        try:
            bot.polling(non_stop=True)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
