import telebot
import sqlite3
import os
import re
import schedule
import threading
import time

from datetime import datetime, timedelta
from googleapiclient.discovery import build


TOKEN = os.getenv("TELEGRAM_TOKEN")
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



def get_owner():
    cursor.execute(
        "SELECT user_id FROM owner LIMIT 1"
    )
    result = cursor.fetchone()

    return result[0] if result else None



def is_owner(message):
    return message.chat.id == get_owner()



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



def update_views():

    cursor.execute("""
    SELECT id, link
    FROM videos
    WHERE platform='YouTube'
    """)

    videos = cursor.fetchall()


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

    db.commit()



def week_start():

    now = datetime.now()

    monday = now - timedelta(days=now.weekday())

    return monday.strftime("%Y-%m-%d")

def send_week_report(chat_id):

    start = week_start()

    cursor.execute("""
    SELECT COUNT(*)
    FROM videos
    WHERE date >= ?
    """, (start,))

    videos = cursor.fetchone()[0]


    cursor.execute("""
    SELECT SUM(views_history.views)
    FROM views_history
    JOIN videos
    ON videos.id = views_history.video_id
    WHERE views_history.date >= ?
    """, (start,))


    views = cursor.fetchone()[0] or 0


    cursor.execute("""
    SELECT videos.link, MAX(views_history.views)
    FROM videos
    JOIN views_history
    ON videos.id = views_history.video_id
    WHERE views_history.date >= ?
    GROUP BY videos.id
    ORDER BY MAX(views_history.views) DESC
    LIMIT 1
    """, (start,))


    best = cursor.fetchone()


    text = (
        "📊 Отчёт недели\n\n"
        f"📅 С {start}\n\n"
        f"🎬 Новых роликов: {videos}\n"
        f"👀 Просмотров: {views}\n"
    )


    if best:
        text += (
            "\n🔥 Лучший ролик:\n"
            f"{best[1]} просмотров\n"
            f"{best[0]}"
        )


    bot.send_message(chat_id, text)



@bot.message_handler(commands=["start"])
def start(message):

    bot.send_message(
        message.chat.id,
        "Привет! Отправь ссылку на TikTok или YouTube Shorts."
    )



@bot.message_handler(commands=["myid"])
def myid(message):

    if get_owner():

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
        "✅ Ты владелец бота."
    )



@bot.message_handler(commands=["update"])
def update_command(message):

    if not is_owner(message):
        return


    update_views()


    bot.send_message(
        message.chat.id,
        "✅ Просмотры обновлены."
    )



@bot.message_handler(commands=["week"])
def week(message):

    if not is_owner(message):
        return

    send_week_report(message.chat.id)



@bot.message_handler(commands=["report"])
def report(message):

    if not is_owner(message):
        return

    send_week_report(message.chat.id)



@bot.message_handler(commands=["top"])
def top(message):

    if not is_owner(message):
        return


    cursor.execute("""
    SELECT videos.link, MAX(views_history.views)
    FROM videos
    JOIN views_history
    ON videos.id = views_history.video_id
    GROUP BY videos.id
    ORDER BY MAX(views_history.views) DESC
    LIMIT 5
    """)


    result = cursor.fetchall()


    text = "🏆 Топ роликов:\n\n"


    for i, row in enumerate(result, 1):

        text += (
            f"{i}. {row[1]} просмотров\n"
            f"{row[0]}\n\n"
        )


    bot.send_message(
        message.chat.id,
        text
    )



@bot.message_handler(
    func=lambda message: not message.text.startswith("/")
)
def save_video(message):

    link = message.text


    if "youtube.com" in link or "youtu.be" in link:

        platform = "YouTube"

    elif "tiktok.com" in link:

        platform = "TikTok"

    else:

        bot.send_message(
            message.chat.id,
            "❌ Нужна ссылка TikTok или YouTube."
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



schedule.every().sunday.at("00:00").do(
    lambda: send_week_report(get_owner())
)



def scheduler():

    while True:

        schedule.run_pending()

        time.sleep(30)



threading.Thread(
    target=scheduler,
    daemon=True
).start()



bot.infinity_polling()
