import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import datetime
from database import fishing_db  # Импортируем нашу базу данных

# Настройка логирования ДО всего остального кода
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация с вашими токенами
BOT_TOKEN = os.getenv('BOT_TOKEN', "8199190847:AAFFnG2fYEd3Zurne8yP1alevSsSeKh5VRk")
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', "d192e284d050cbe679c3641f372e7a02")

class FishingBot:
    def __init__(self):
        self.weather_cache = {}
        self.cache_timeout = 1800  # 30 минут

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        keyboard = [['🎣 Погода и клёв'], ['📊 Помощь']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        welcome_text = f"""
👋 Привет, {user.first_name}! Я твой рыболовный помощник!

🌤 Я могу показать погоду в любом городе и спрогнозировать клёв рыбы.

🎯 Просто нажми кнопку «🎣 Погода и клёв» или отправь название города!
        """
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    async def send_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать справку"""
        help_text = """
🎣 *Рыболовный помощник*

*Команды:*
/start - начать работу
/weather [город] - погода и клёв
/spots [город] - рыболовные места
/fish [вид рыбы] - места для ловли
/reports - последние отчеты
/help - эта справка

*Как использовать:*
1. Нажмите кнопку «🎣 Погода и клёв»
2. Отправьте название города (например: Москва)
3. Получите детальный прогноз!

*Факторы влияющие на клёв:*
✅ *Отличный*: стабильное давление, температура 15-25°C, легкий ветер
👍 *Хороший*: небольшие изменения погоды
⚡ *Средний*: умеренные изменения
👎 *Плохой*: резкие перепады, сильный ветер, гроза
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    def get_weather(self, city: str) -> dict:
        """Получить данные о погоде"""
        try:
            # Проверка кэша
            cache_key = city.lower()
            if cache_key in self.weather_cache:
                cached_data = self.weather_cache[cache_key]
                if datetime.now().timestamp() - cached_data['timestamp'] < self.cache_timeout:
                    return cached_data['data']

            # Запрос к API погоды
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Weather API error: {response.status_code}")
                return None

            data = response.json()
            
            weather_data = {
                'city': data['name'],
                'temp': round(data['main']['temp']),
                'feels_like': round(data['main']['feels_like']),
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'wind_speed': data['wind']['speed'],
                'description': data['weather'][0]['description'].capitalize(),
                'weather_main': data['weather'][0]['main'],
                'country': data.get('sys', {}).get('country', '')
            }

            # Сохранение в кэш
            self.weather_cache[cache_key] = {
                'timestamp': datetime.now().timestamp(),
                'data': weather_data
            }

            return weather_data

        except Exception as e:
            logger.error(f"Error getting weather: {e}")
            return None

    def calculate_fishing_conditions(self, weather_data: dict) -> dict:
        """Рассчитать условия для рыбалки"""
        temp = weather_data['temp']
        pressure = weather_data['pressure']
        wind_speed = weather_data['wind_speed']
        weather_main = weather_data['weather_main']

        score = 0

        # Температура (оптимально 15-25°C)
        if 15 <= temp <= 25:
            temp_score = 3
        elif 10 <= temp < 15 or 25 < temp <= 30:
            temp_score = 2
        elif 5 <= temp < 10 or 30 < temp <= 35:
            temp_score = 1
        else:
            temp_score = 0
        score += temp_score

        # Давление (оптимально 740-750 мм рт.ст.)
        pressure_mm = pressure * 0.750062
        if 740 <= pressure_mm <= 750:
            pressure_score = 3
        elif 735 <= pressure_mm < 740 or 750 < pressure_mm <= 755:
            pressure_score = 2
        elif 730 <= pressure_mm < 735 or 755 < pressure_mm <= 760:
            pressure_score = 1
        else:
            pressure_score = 0
        score += pressure_score

        # Ветер
        if wind_speed < 3:
            wind_score = 3
        elif 3 <= wind_speed < 6:
            wind_score = 2
        elif 6 <= wind_speed < 10:
            wind_score = 1
        else:
            wind_score = 0
        score += wind_score

        # Погодные условия
        if weather_main in ['Clear']:
            weather_score = 3
        elif weather_main in ['Clouds']:
            weather_score = 2
        elif weather_main in ['Drizzle', 'Mist']:
            weather_score = 1
        else:
            weather_score = 0
        score += weather_score

        # Определение рейтинга клёва
        max_score = 12
        if score >= 10:
            rating = "Отличный"
            emoji = "🔥"
            color = "🟢"
            advice = "Идеальный день для рыбалки!"
        elif score >= 7:
            rating = "Хороший"
            emoji = "👍"
            color = "🟡"
            advice = "Хорошие условия для ловли"
        elif score >= 4:
            rating = "Средний"
            emoji = "⚡"
            color = "🟠"
            advice = "Можно попробовать половить"
        else:
            rating = "Плохой"
            emoji = "👎"
            color = "🔴"
            advice = "Рыба может не клевать"

        # Рекомендации по снастям
        if score >= 8:
            spinning = "Отличный"
            fishing_rod = "Отличный"
        elif score >= 5:
            spinning = "Хороший"
            fishing_rod = "Хороший"
        elif score >= 3:
            spinning = "Средний"
            fishing_rod = "Средний"
        else:
            spinning = "Плохой"
            fishing_rod = "Плохой"

        return {
            'rating': rating,
            'emoji': emoji,
            'color': color,
            'advice': advice,
            'spinning': spinning,
            'fishing_rod': fishing_rod,
            'score': score,
            'max_score': max_score,
            'pressure_mm': round(pressure_mm, 1)
        }

    async def handle_weather_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик запроса погоды"""
        city = None
        
        if context.args:
            city = ' '.join(context.args)
        elif update.message.text and update.message.text not in ['🎣 Погода и клёв', '📊 Помощь']:
            city = update.message.text

        if not city:
            await update.message.reply_text("🌤 Введите название города:\n\nНапример: Москва")
            return

        await update.message.reply_chat_action(action='typing')

        # Получаем данные о погоде
        weather_data = self.get_weather(city)
        
        if not weather_data:
            await update.message.reply_text(
                "❌ Не удалось найти город. Проверьте название и попробуйте снова.\n\n"
                "Примеры:\n• Москва\n• Санкт-Петербург\n• Новосибирск"
            )
            return

        # Рассчитываем условия для рыбалки
        fishing_conditions = self.calculate_fishing_conditions(weather_data)

        # Формируем сообщение
        message = f"""
{weather_data['description']} *в {weather_data['city']}, {weather_data['country']}*

🌡 *Температура:* {weather_data['temp']}°C
💨 *Ветер:* {weather_data['wind_speed']} м/с
💧 *Влажность:* {weather_data['humidity']}%
📊 *Давление:* {fishing_conditions['pressure_mm']} мм рт.ст.

{fishing_conditions['color']} *ПРОГНОЗ КЛЁВА:* {fishing_conditions['rating']} {fishing_conditions['emoji']}

🎣 *Спиннинг:* {fishing_conditions['spinning']}
🎏 *Поплавочная удочка:* {fishing_conditions['fishing_rod']}

*Оценка:* {fishing_conditions['score']}/{fishing_conditions['max_score']} баллов
*Совет:* {fishing_conditions['advice']}
        """

        await update.message.reply_text(message, parse_mode='Markdown')

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

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        text = update.message.text
        
        if text == '📊 Помощь':
            await self.send_help(update, context)
        elif text == '🎣 Погода и клёв':
            await update.message.reply_text("🌤 Отправьте название города:\n\nНапример: Москва")
        else:
            await self.handle_weather_request(update, context)

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

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}")
        if update and update.message:
            await update.message.reply_text("⚠️ Произошла ошибка. Попробуйте позже.")

def main():
    """Основная функция"""
    logger.info("Запуск бота...")
    logger.info(f"BOT_TOKEN: {'установлен' if BOT_TOKEN else 'не установлен'}")
    logger.info(f"WEATHER_API_KEY: {'установлен' if WEATHER_API_KEY else 'не установлен'}")
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен!")
        return
    
    if not WEATHER_API_KEY:
        logger.error("❌ WEATHER_API_KEY не установлен!")
        return
    
    # Создание бота
    fishing_bot = FishingBot()
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавление обработчиков
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
