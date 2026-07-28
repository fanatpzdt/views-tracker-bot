import telebot
import sqlite3
from datetime import datetime

TOKEN = "8206628983:AAHhyn26UBXgGwOEiD49_399KPASmsRD30I"

bot = telebot.TeleBot(TOKEN)

db = sqlite3.connect("videos.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link TEXT,
    platform TEXT,
    views INTEGER DEFAULT 0,
    date TEXT
)
""")

db.commit()


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! Отправь ссылку на TikTok или YouTube Shorts."
    )


@bot.message_handler(func=lambda message: True)
def save_link(message):
    link = message.text

    if "tiktok.com" in link:
        platform = "TikTok"
    elif "youtube.com" in link or "youtu.be" in link:
        platform = "YouTube"
    else:
        bot.send_message(
            message.chat.id,
            "❌ Нужна ссылка TikTok или YouTube Shorts"
        )
        return

    date = datetime.now().strftime("%d.%m.%Y")

    cursor.execute(
        "INSERT INTO videos (link, platform, date) VALUES (?, ?, ?)",
        (link, platform, date)
    )

    db.commit()

    bot.send_message(
        message.chat.id,
        f"✅ Сохранил!\n"
        f"Платформа: {platform}\n"
        f"Дата: {date}"
    )


@bot.message_handler(commands=['stats'])
def stats(message):
    cursor.execute("""
    SELECT platform, COUNT(*) 
    FROM videos 
    GROUP BY platform
    """)

    result = cursor.fetchall()

    text = "📊 Статистика:\n"

    for platform, count in result:
        text += f"{platform}: {count} роликов\n"

    bot.send_message(message.chat.id, text)


bot.infinity_polling()

