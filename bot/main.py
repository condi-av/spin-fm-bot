import os, asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from keyboards import regions_kb
from regions import REGIONS
from forecast import get_forecast
from rss import fetch_new_posts          # 2.1-2.2
from db import init_db                   # 2.2

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
    await m.answer("👋 Выбери регион:", reply_markup=regions_kb())

@dp.callback_query(lambda c: c.data.startswith("reg_page_"))
async def region_page(c: types.CallbackQuery):
    page = int(c.data.split("_")[-1])
    await c.message.edit_reply_markup(reply_markup=regions_kb(page))

@dp.callback_query(F.data == "bite")
async def bite(c: types.CallbackQuery):
    await c.answer()
    await c.message.answer("Пока просто заглушка: клюёт! 😄")

# ---------- прогноз клева ----------
@dp.callback_query(F.data.in_(REGIONS.values()))
async def region_selected(c: types.CallbackQuery):
    region_name = next(k for k, v in REGIONS.items() if v == c.data)
    forecast = await get_forecast(region_name)
    text = (
        f"🎣 <b>{forecast['region']}</b>\n"
        f"🌡 Температура: {forecast['temp']} °C\n"
        f"📊 Давление: {forecast['pressure']} мм\n"
        f"🌕 Луна: {forecast['moon']} %\n"
        f"⭐ Оценка клева: {forecast['score']}/100\n\n"
        f"{forecast['advice']}"
    )
    await c.message.answer(text, parse_mode="HTML")

# ---------- RSS-автопост 3 раза в день (2.3) ----------
async def post_news():
    posts = await fetch_new_posts()   # только новые
    if not posts:
        return
    p = posts[0]                      # 1 пост
    text = f"<b>{p['title']}</b>\n\n{p['summary']}\n\n{p['link']}"
    await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")

# ---------- запуск ----------
async def main():
    await init_db()                   # создаём SQLite если нет
    scheduler = AsyncIOScheduler()
    # 08:00, 14:00, 20:00 по Москве
    moscow = CronTrigger(hour="8,14,20", minute=0, timezone="Europe/Moscow")
    scheduler.add_job(post_news, moscow)
    scheduler.start()

    asyncio.create_task(web_app())    # слушаем port 10000
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
