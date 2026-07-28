import telebot
import sqlite3
from datetime import datetime

TOKEN = "8206628983:AAHhyn26UBXgGwOEiD49_399KPASmsRD30I"

bot = telebot.TeleBot(TOKEN)

# создаём базу
db = sqlite3.connect("videos.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link TEXT,
    date TEXT
)
""")

db.commit()


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! Отправь мне ссылку на TikTok или YouTube Shorts."
    )


@bot.message_handler(func=lambda message: True)
def save_link(message):
    link = message.text
    date = datetime.now().strftime("%d.%m.%Y")

    cursor.execute(
        "INSERT INTO videos (link, date) VALUES (?, ?)",
        (link, date)
    )

    db.commit()

    cursor.execute("SELECT COUNT(*) FROM videos")
    count = cursor.fetchone()[0]

    bot.send_message(
        message.chat.id,
        f"✅ Сохранил!\n"
        f"Дата: {date}\n"
        f"Всего роликов: {count}"
    )


@bot.message_handler(commands=['stats'])
def stats(message):
    cursor.execute("SELECT COUNT(*) FROM videos")
    count = cursor.fetchone()[0]

    bot.send_message(
        message.chat.id,
        f"📊 Всего добавлено роликов: {count}"
    )


bot.infinity_polling()
