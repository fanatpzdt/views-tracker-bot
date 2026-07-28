import telebot
from datetime import datetime

TOKEN = "8206628983:AAHhyn26UBXgGwOEiD49_399KPASmsRD30I"

bot = telebot.TeleBot(TOKEN)

videos = []

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! Я бот для учёта просмотров.\n"
        "Отправь мне ссылку на TikTok или YouTube Shorts."
    )

@bot.message_handler(func=lambda message: True)
def save_link(message):
    link = message.text
    date = datetime.now().strftime("%d.%m.%Y")

    videos.append({
        "link": link,
        "date": date
    })

    bot.send_message(
        message.chat.id,
        f"✅ Сохранил!\nДата: {date}\nВсего роликов: {len(videos)}"
    )

@bot.message_handler(commands=['stats'])
def stats(message):
    bot.send_message(
        message.chat.id,
        f"📊 Роликов за всё время: {len(videos)}"
    )

bot.infinity_polling()
