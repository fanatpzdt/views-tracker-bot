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


db = sqlite3.connect(
    "videos.db",
    check_same_thread=False
)

cursor = db.cursor()


# =========================
# DATABASE
# =========================


cursor.execute("""
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link TEXT,
    video_id TEXT,
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



# =========================
# OWNER
# =========================


def get_owner():

    cursor.execute(
        "SELECT user_id FROM owner LIMIT 1"
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    return None



def is_owner(message):

    return message.chat.id == get_owner()



# =========================
# DATES
# =========================


def week_start():

    now = datetime.now()

    monday = now - timedelta(
        days=now.weekday()
    )

    return monday.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )



def week_end():

    return (
        week_start()
        + timedelta(days=6)
    ).replace(
        hour=23,
        minute=59,
        second=59
    )



# =========================
# YOUTUBE
# =========================


def extract_video_id(link):

    match = re.search(
        r"(?:shorts/|watch\?v=|youtu.be/)([^&?/]+)",
        link
    )

    if match:
        return match.group(1)

    return None



def get_views(video_id):

    youtube = build(
        "youtube",
        "v3",
        developerKey=YOUTUBE_API_KEY
    )


    result = youtube.videos().list(
        part="statistics",
        id=video_id
    ).execute()


    if result.get("items"):

        return int(
            result["items"][0]
            ["statistics"]
            ["viewCount"]
        )


    return 0



# =========================
# UPDATE VIEWS
# =========================


def update_views():

    cursor.execute(
        """
        SELECT id, video_id
        FROM videos
        """
    )

    videos = cursor.fetchall()


    today = datetime.now().strftime(
        "%Y-%m-%d"
    )


    for db_id, youtube_id in videos:

        views = get_views(
            youtube_id
        )


        cursor.execute(
            """
            INSERT INTO views_history
            (video_id, views, date)
            VALUES (?, ?, ?)
            """,
            (
                db_id,
                views,
                today
            )
        )


    db.commit()

# =========================
# REPORTS
# =========================


def get_week_views():

    start = week_start().strftime(
        "%Y-%m-%d"
    )


    end = week_end().strftime(
        "%Y-%m-%d"
    )


    cursor.execute(
        """
        SELECT video_id, views
        FROM views_history
        WHERE date BETWEEN ? AND ?
        ORDER BY date ASC
        """,
        (
            start,
            end
        )
    )


    history = cursor.fetchall()


    totals = {}


    for video_id, views in history:

        if video_id not in totals:

            totals[video_id] = []

        totals[video_id].append(
            views
        )


    results = []


    for video_id, values in totals.items():

        if len(values) > 0:

            growth = (
                values[-1]
                -
                values[0]
            )

            if growth < 0:
                growth = 0


            results.append(
                growth
            )


    return sorted(
        results,
        reverse=True
    )



def make_report(title):

    start = week_start()

    end = week_end()


    cursor.execute(
        """
        SELECT COUNT(*)
        FROM videos
        WHERE date BETWEEN ? AND ?
        """,
        (
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d")
        )
    )


    count = cursor.fetchone()[0]


    views = get_week_views()


    total = sum(views)


    text = (
        f"📊 {title}\n\n"
        f"📅 "
        f"{start.strftime('%d.%m')}"
        f" - "
        f"{end.strftime('%d.%m')}\n\n"
        f"🎬 Роликов: {count}\n\n"
        f"👀 Просмотров: {total}\n\n"
        f"🏆 ТОП-3:\n"
    )


    for i, value in enumerate(
        views[:3],
        1
    ):

        text += (
            f"{i}. {value}\n"
        )


    return text



def send_daily_report():

    owner = get_owner()

    if owner:

        update_views()

        bot.send_message(
            owner,
            make_report(
                "Статистика дня"
            )
        )



def send_week_report():

    owner = get_owner()

    if owner:

        update_views()

        bot.send_message(
            owner,
            make_report(
                "Итоги недели"
            )
        )



# =========================
# COMMANDS
# =========================


@bot.message_handler(
    commands=["start"]
)
def start(message):

    bot.send_message(
        message.chat.id,
        "Отправь ссылку на YouTube Shorts."
    )



@bot.message_handler(
    commands=["myid"]
)
def myid(message):

    if get_owner():

        bot.send_message(
            message.chat.id,
            "Владелец уже установлен."
        )

        return


    cursor.execute(
        """
        INSERT INTO owner(user_id)
        VALUES(?)
        """,
        (
            message.chat.id,
        )
    )


    db.commit()


    bot.send_message(
        message.chat.id,
        "✅ Владелец добавлен."
    )



@bot.message_handler(
    commands=["update"]
)
def update_command(message):

    if not is_owner(message):
        return


    update_views()


    bot.send_message(
        message.chat.id,
        "✅ Просмотры обновлены."
    )

@bot.message_handler(
    commands=["week"]
)
def week_command(message):

    if not is_owner(message):
        return


    bot.send_message(
        message.chat.id,
        make_report(
            "Статистика недели"
        )
    )



@bot.message_handler(
    commands=["report"]
)
def report_command(message):

    if not is_owner(message):
        return


    bot.send_message(
        message.chat.id,
        make_report(
            "Итоги недели"
        )
    )



# =========================
# SAVE YOUTUBE SHORT
# =========================


@bot.message_handler(
    func=lambda message:
    not message.text.startswith("/")
)

@bot.message_handler(
    func=lambda message:
    not message.text.startswith("/")
)
def save_video(message):

    link = message.text

    video_id = extract_video_id(link)

    if not video_id:

        bot.send_message(
            message.chat.id,
            "❌ Нужна ссылка YouTube Shorts."
        )

        return


    cursor.execute(
        """
        SELECT id
        FROM videos
        WHERE video_id = ?
        """,
        (video_id,)
    )

    exists = cursor.fetchone()


    if exists:

        bot.send_message(
            message.chat.id,
            "⚠️ Этот ролик уже добавлен."
        )

        return


    cursor.execute(
        """
        INSERT INTO videos
        (link, video_id, date)
        VALUES (?, ?, ?)
        """,
        (
            link,
            video_id,
            datetime.now().strftime(
                "%Y-%m-%d"
            )
        )
    )


    db.commit()


    bot.send_message(
        message.chat.id,
        "✅ Shorts сохранён."
    )



# =========================
# AUTOMATION
# =========================


# каждый день в 00:00
schedule.every().day.at(
    "00:00"
).do(
    send_daily_report
)


# понедельник 00:05
# итог прошлой недели
schedule.every().monday.at(
    "00:05"
).do(
    send_week_report
)



def scheduler():

    while True:

        schedule.run_pending()

        time.sleep(30)



threading.Thread(
    target=scheduler,
    daemon=True
).start()



# =========================
# START BOT
# =========================


bot.infinity_polling()
