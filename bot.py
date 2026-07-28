import telebot
import sqlite3
import os
import re
from datetime import datetime

from googleapiclient.discovery import build

TOKEN = "8206628983:AAHhyn26UBXgGwOEiD49_399KPASmsRD30I"
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

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


def get_youtube_views(link):

    match = re.search(r"(?:v=|youtu.be/|shorts/)([^&?/]+)", link)

    if not match:
        return None

    video_id = match.group(1)

    youtube = build(
        "youtube",
        "v3",
        developerKey=YOUTUBE_API_KEY
    )

    response = youtube.videos().list(
        part="statistics",
        id=video_id
    ).execute()

    if response.get("items"):
        views = response["items"][0]["statistics"].get("viewCount")
        return int(views)

    return None


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! Отправь ссылку на TikTok или YouTube Shorts."
    )


@bot.message_handler(commands=["stats"])
def stats(message):

    cursor.execute("""
    SELECT platform, COUNT(*), SUM(views)
    FROM videos
    GROUP BY platform
    """)

    result = cursor.fetchall()

    text = "📊 Статистика:\n\n"

    for platform, count, views in result:
        text += (
            f"{platform}\n"
            f"Роликов: {count}\n"
            f"Просмотров: {views or 0}\n\n"
        )

    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda message: not message.text.startswith("/"))
def save_video(message):

    link = message.text

    views = 0

    if "youtube.com" in link or "youtu.be" in link:

        platform = "YouTube"

        try:
            views = get_youtube_views(link) or 0
        except:
            views = 0

    elif "tiktok.com" in link:

        platform = "TikTok"

    else:
        bot.send_message(
            message.chat.id,
            "❌ Нужна ссылка TikTok или YouTube Shorts"
        )
        return


    date = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        """
        INSERT INTO videos
        (link, platform, views, date)
        VALUES (?, ?, ?, ?)
        """,
        (link, platform, views, date)
    )

    db.commit()


    bot.send_message(
        message.chat.id,
        f"✅ Сохранил!\n"
        f"Платформа: {platform}\n"
        f"Просмотры: {views}"
    )


bot.infinity_polling()
