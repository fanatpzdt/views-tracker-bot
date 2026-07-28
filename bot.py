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
    date TEXT
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS views_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER,
    views INTEGER,
    date TEXT
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS owner (
    id INTEGER PRIMARY KEY,
    user_id INTEGER
)
""")


db.commit()



def is_owner(message):

    cursor.execute(
        "SELECT user_id FROM owner LIMIT 1"
    )

    owner = cursor.fetchone()

    return owner and owner[0] == message.chat.id



def get_youtube_views(link):

    match = re.search(
        r"(?:v=|youtu.be/|shorts/)([^&?/]+)",
        link
    )

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
        return int(
            response["items"][0]["statistics"]["viewCount"]
        )

    return None



@bot.message_handler(commands=["start"])
def start(message):

    bot.send_message(
        message.chat.id,
        "Привет! Я твой трекер просмотров."
    )



@bot.message_handler(commands=["myid"])
def myid(message):

    cursor.execute(
        "SELECT user_id FROM owner LIMIT 1"
    )

    owner = cursor.fetchone()


    if owner:
        bot.send_message(
            message.chat.id,
            "⚠️ Владелец уже установлен."
        )
        return


    cursor.execute(
        "INSERT INTO owner (user_id) VALUES (?)",
        (message.chat.id,)
    )

    db.commit()


    bot.send_message(
        message.chat.id,
        "✅ Ты добавлен как владелец бота."
    )



@bot.message_handler(commands=["report"])
def report(message):

    if not is_owner(message):
        bot.send_message(
            message.chat.id,
            "❌ Нет доступа."
        )
        return


    cursor.execute(
        "SELECT COUNT(*) FROM videos"
    )

    videos = cursor.fetchone()[0]


    cursor.execute(
        "SELECT SUM(views) FROM views_history"
    )

    views = cursor.fetchone()[0] or 0


    bot.send_message(
        message.chat.id,
        f"📊 Отчёт:\n\n"
        f"Роликов: {videos}\n"
        f"Просмотров: {views}"
    )



@bot.message_handler(commands=["update"])
def update_views(message):

    if not is_owner(message):
        return


    cursor.execute("""
    SELECT id, link
    FROM videos
    WHERE platform='YouTube'
    """)

    videos = cursor.fetchall()


    count = 0


    for video_id, link in videos:

        views = get_youtube_views(link)

        if views is not None:

            cursor.execute(
                """
                INSERT INTO views_history
                (video_id, views, date)
                VALUES (?, ?, ?)
                """,
                (
                    video_id,
                    views,
                    datetime.now().strftime("%Y-%m-%d")
                )
            )

            count += 1


    db.commit()


    bot.send_message(
        message.chat.id,
        f"✅ Обновлено роликов: {count}"
    )



@bot.message_handler(func=lambda message: not message.text.startswith("/"))
def save_video(message):

    link = message.text


    if "youtube.com" in link or "youtu.be" in link:
        platform = "YouTube"

    elif "tiktok.com" in link:
        platform = "TikTok"

    else:
        bot.send_message(
            message.chat.id,
            "❌ Нужна ссылка TikTok или YouTube Shorts."
        )
        return


    cursor.execute(
        """
        INSERT INTO videos
        (link, platform, date)
        VALUES (?, ?, ?)
        """,
        (
            link,
            platform,
            datetime.now().strftime("%Y-%m-%d")
        )
    )

    db.commit()


    bot.send_message(
        message.chat.id,
        "✅ Ролик сохранён."
    )


bot.infinity_polling()
