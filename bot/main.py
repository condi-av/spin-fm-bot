import os, asyncio, threading
import feedparser
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@SpinFM_Rus"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- веб-health-check ----------
async def health(_: web.Request) -> web.Response:
    return web.Response(text="OK")

async def web_app():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

# ---------- команды ----------
@dp.message(Command("start"))
async def start(m: types.Message):
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🎣 Клёв в моём регионе", callback_data="bite")]
        ]
    )
    await m.answer("👋 Привет! Я SpinFM-бот. Жми кнопку ниже.", reply_markup=kb)

@dp.callback_query(F.data == "bite")
async def bite(c: types.CallbackQuery):
    await c.answer()
    await c.message.answer("Пока просто заглушка: клюёт! 😄")

# ---------- парсер новостей ----------
async def post_news():
    url = "https://fishering.ru/feed/"
    feed = feedparser.parse(url)
    for entry in feed.entries[:1]:
        text = f"<b>{entry.title}</b>\n\n{entry.summary}\n\n{entry.link}"
        await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")

# ---------- запуск ----------
async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(post_news, "interval", hours=3)
    scheduler.start()

    asyncio.create_task(web_app())   # стартуем веб
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
