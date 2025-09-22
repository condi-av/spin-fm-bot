import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import datetime
from database import fishing_db  # Импортируем нашу базу данных

# ... остальной код остается таким же ...

class FishingBot:
    def __init__(self):
        self.weather_cache = {}
        self.cache_timeout = 1800
        
    # ... существующие методы остаются без изменений ...

    async def show_fishing_spots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать рыболовные места в городе"""
        city = ' '.join(context.args) if context.args else None
        
        if not city:
            await update.message.reply_text("Укажите город: /spots Москва")
            return
        
        spots = fishing_db.get_spots_by_city(city.lower())
        
        if not spots:
            await update.message.reply_text(
                f"❌ Не найдено рыболовных мест в городе {city}\n\n"
                f"Попробуйте:\n• Москва\n• Санкт-Петербург\n• Новосибирск\n• Екатеринбург"
            )
            return
        
        message = f"🎣 *Рыболовные места в {city.title()}*\n\n"
        
        for i, spot in enumerate(spots, 1):
            rating_stars = "⭐" * int(spot['avg_rating']) if spot['avg_rating'] > 0 else "☆"
            message += f"{i}. *{spot['name']}* ({spot['type']}) {rating_stars}\n"
            message += f"   🐟: {spot['fish_species']}\n"
            message += f"   📍: {spot['description']}\n"
            message += f"   🕒: {spot['best_season']}\n"
            message += f"   💰: {spot['access_type']}\n\n"
        
        # Кнопки для интерактива
        keyboard = [
            [InlineKeyboardButton("🗺️ Показать на карте", callback_data=f"map_{city}")],
            [InlineKeyboardButton("📊 Добавить отчет", callback_data=f"report_{city}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

    async def search_spots_by_fish(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поиск мест по виду рыбы"""
        fish_species = ' '.join(context.args) if context.args else None
        
        if not fish_species:
            await update.message.reply_text("Укажите вид рыбы: /fish щука")
            return
        
        spots = fishing_db.get_spots_by_fish(fish_species.lower())
        
        if not spots:
            await update.message.reply_text(
                f"❌ Не найдено мест для ловли {fish_species}\n\n"
                f"Попробуйте:\n• щука\n• карп\n• окунь\n• лещ\n• судак"
            )
            return
        
        message = f"🎣 *Места для ловли {fish_species.title()}*\n\n"
        
        for i, spot in enumerate(spots[:5], 1):  # Ограничиваем 5 местами
            message += f"{i}. *{spot['name']}* ({spot['city'].title()})\n"
            message += f"   📍: {spot['description']}\n"
            message += f"   🕒: {spot['best_season']}\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')

    async def show_recent_reports(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать последние отчеты о рыбалке"""
        reports = fishing_db.get_recent_reports(limit=5)
        
        if not reports:
            await update.message.reply_text("📊 Пока нет отчетов о рыбалке")
            return
        
        message = "📊 *Последние отчеты о рыбалке*\n\n"
        
        for report in reports:
            message += f"📍 *{report['spot_name']}*\n"
            message += f"🐟 Поймали: {report['fish_caught']}\n"
            message += f"⭐ Оценка: {'⭐' * report['rating']}\n"
            if report['comment']:
                message += f"💬: {report['comment']}\n"
            message += f"📅: {report['report_date']}\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback-запросов от кнопок"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith('map_'):
            city = data.replace('map_', '')
            await query.edit_message_text(f"🗺️ Функция карты для {city} в разработке...")
        
        elif data.startswith('report_'):
            city = data.replace('report_', '')
            await query.edit_message_text(f"📊 Функция отчетов для {city} в разработке...")

def main():
    """Основная функция"""
    logger.info("Запуск бота...")
    logger.info(f"BOT_TOKEN: {'установлен' if BOT_TOKEN else 'не установлен'}")
    logger.info(f"WEATHER_API_KEY: {'установлен' if WEATHER_API_KEY else 'не установлен'}")
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен!")
        return
    
    # Создание бота
    fishing_bot = FishingBot()
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавление обработчиков (старые + новые)
    application.add_handler(CommandHandler("start", fishing_bot.start))
    application.add_handler(CommandHandler("help", fishing_bot.send_help))
    application.add_handler(CommandHandler("weather", fishing_bot.handle_weather_request))
    application.add_handler(CommandHandler("spots", fishing_bot.show_fishing_spots))
    application.add_handler(CommandHandler("fish", fishing_bot.search_spots_by_fish))
    application.add_handler(CommandHandler("reports", fishing_bot.show_recent_reports))
    
    # Обработчик callback-запросов
    application.add_handler(CallbackQueryHandler(fishing_bot.handle_callback))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fishing_bot.handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(fishing_bot.error_handler)

    # Запуск бота
    logger.info("Запуск бота в режиме polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
