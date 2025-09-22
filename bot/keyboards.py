from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from regions import REGIONS

def regions_kb(page: int = 0, per_page: int = 10):
    builder = InlineKeyboardBuilder()
    regs = list(REGIONS.items())
    start, end = page * per_page, (page + 1) * per_page
    for name, cb in regs[start:end]:
        builder.button(text=name, callback_data=cb)
    builder.adjust(1)

    nav = []
    if page > 0:
        nav.append(("⬅ Назад", f"reg_page_{page-1}"))
    if end < len(regs):
        nav.append(("Вперёд ➡", f"reg_page_{page+1}"))
    if nav:
        nav_buttons = []
        for text, cb in nav:
            nav_buttons.append(types.InlineKeyboardButton(text=text, callback_data=cb))
        builder.row(*nav_buttons)
    return builder.as_markup()
