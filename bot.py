import telebot
import sqlite3
import os
import re

from datetime import datetime
from googleapiclient.discovery import build


TOKEN = "ТВОЙ_ТОКЕН_ОТ_BOTFATHER"
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


db.commit()



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
        views = response["items"][0]["statistics"].get("viewCount")
        return int(views)

    return None



@bot.message_handler(commands=["start"])
def start(message):

    bot.send_message(
        message.chat.id,
        "Привет! Отправь ссылку на TikTok или YouTube Shorts."
    )



@bot.message_handler(commands=["update"])
def update_views(message):

    cursor.execute("""
    SELECT id, link, platform
    FROM videos
    WHERE platform='YouTube'
    """)

    videos = cursor.fetchall()


    updated = 0


    for video in videos:

        video_id, link, platform = video

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

            updated += 1


    db.commit()


    bot.send_message(
        message.chat.id,
        f"✅ Проверено роликов: {updated}"
    )



@bot.message_handler(commands=["top"])
def top(message):

    cursor.execute("""
    SELECT 
    videos.link,
    MAX(views_history.views)

    FROM videos

    JOIN views_history
    ON videos.id = views_history.video_id

    GROUP BY videos.id

    ORDER BY MAX(views_history.views) DESC

    LIMIT 5
    """)


    result = cursor.fetchall()


    if not result:
        bot.send_message(
            message.chat.id,
            "Пока нет статистики."
        )
        return


    text = "🏆 Топ роликов:\n\n"


    for i, item in enumerate(result, start=1):

        link, views = item

        text += (
            f"{i}. {views} просмотров\n"
            f"{link}\n\n"
        )


    bot.send_message(
        message.chat.id,
        text
    )



@bot.message_handler(commands=["stats"])
def stats(message):

    cursor.execute("""
    SELECT COUNT(*)
    FROM videos
    """)

    count = cursor.fetchone()[0]


    cursor.execute("""
    SELECT SUM(views)
    FROM views_history
    """)

    views = cursor.fetchone()[0] or 0


    bot.send_message(
        message.chat.id,
        f"📊 Статистика:\n\n"
        f"Роликов: {count}\n"
        f"Просмотров: {views}"
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
            "❌ Нужна ссылка TikTok или YouTube Shorts"
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
        "✅ Ролик сохранён"
    )



bot.infinity_polling()
