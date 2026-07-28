import telebot
import sqlite3
from datetime import datetime, timedelta

TOKEN = "8206628983:AAHhyn26UBXgGwOEiD49_399KPASmsRD30I"

bot = telebot.TeleBot(TOKEN)

db = sqlite3.connect("videos.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link TEXT,
    platform TEXT,
    date TEXT
)
""")

db.commit()


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! Я бот для учёта TikTok и YouTube Shorts.\n"
        "Отправь ссылку на ролик."
    )


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "📌 Команды:\n\n"
        "/week — статистика за эту неделю\n"
        "/stats — общая статистика\n"
        "/all — последние ролики\n"
        "/help — помощь"
    )


@bot.message_handler(commands=['stats'])
def stats(message):
    cursor.execute("""
    SELECT platform, COUNT(*)
    FROM videos
    GROUP BY platform
    """)

    result = cursor.fetchall()

    if not result:
        bot.send_message(
            message.chat.id,
            "📊 Пока нет роликов."
        )
        return

    text = "📊 Общая статистика:\n\n"

    for platform, count in result:
        text += f"{platform}: {count} роликов\n"

    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['week'])
def week(message):

    today = datetime.now()
    monday = today - timedelta(days=today.weekday())

    monday = monday.replace(
        hour=0,
        minute=0,
        second=0
    )

    cursor.execute("""
    SELECT platform, COUNT(*)
    FROM videos
    WHERE date >= ?
    GROUP BY platform
    """,
    (monday.strftime("%Y-%m-%d"),))

    result = cursor.fetchall()

    if not result:
        bot.send_message(
            message.chat.id,
            "📊 За эту неделю роликов пока нет."
        )
        return

    text = "📊 Статистика недели:\n\n"
    total = 0

    for platform, count in result:
        text += f"{platform}: {count} роликов\n"
        total += count

    text += f"\nВсего: {total} роликов"

    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['all'])
def all_videos(message):

    cursor.execute("""
    SELECT platform, date, link
    FROM videos
    ORDER BY id DESC
    LIMIT 10
    """)

    videos = cursor.fetchall()

    if not videos:
        bot.send_message(
            message.chat.id,
            "📋 Список пуст."
        )
        return

    text = "📋 Последние ролики:\n\n"

    for i, video in enumerate(videos, start=1):
        platform, date, link = video

        text += (
            f"{i}. {platform}\n"
            f"📅 {date}\n"
            f"🔗 {link}\n\n"
        )

    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda message: not message.text.startswith('/'))
def save_link(message):

    link = message.text

    if "tiktok.com" in link:
        platform = "TikTok"

    elif "youtube.com" in link or "youtu.be" in link:
        platform = "YouTube"

    else:
        bot.send_message(
            message.chat.id,
            "❌ Отправь ссылку TikTok или YouTube Shorts."
        )
        return

    date = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        "INSERT INTO videos (link, platform, date) VALUES (?, ?, ?)",
        (link, platform, date)
    )

    db.commit()

    bot.send_message(
        message.chat.id,
        f"✅ Сохранил!\n"
        f"Платформа: {platform}"
    )


bot.infinity_polling()
