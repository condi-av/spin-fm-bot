import os, feedparser, asyncio
from aiogram import Bot, Dispatcher, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler

BOT_TOKEN = os.getenv("BOT_TOKEN")          # из переменных окружения
CHANNEL_ID = "@SpinFM_Rus"                  # наш канал

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# -------- команды --------
@dp.message(commands=["start"])
async def start(m: types.Message):
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🎣 Клёв в моём регионе", callback_data="bite")]
        ]
    )
    await m.answer("👋 Привет! Я SpinFM-бот. Жми кнопку ниже.", reply_markup=kb)

@dp.callback_query(lambda c: c.data == "bite")
async def bite(c: types.CallbackQuery):
    await c.answer()
    await c.message.answer("Пока просто заглушка: клюёт! 😄")

# -------- парсер новостей --------
async def post_news():
    url = "https://fishering.ru/feed/"   # пример
    feed = feedparser.parse(url)
    for entry in feed.entries[:1]:       # 1 пост за раз
        text = f"<b>{entry.title}</b>\n\n{entry.summary}\n\n{entry.link}"
        await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")

# -------- запуск --------
async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(post_news, "interval", hours=3)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())
