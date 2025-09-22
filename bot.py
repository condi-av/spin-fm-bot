import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import datetime
from database import fishing_db

# Настройка логирования
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
        
        # Расширенная клавиатура со всеми функциями
        keyboard = [
            ['🎣 Погода и клёв', '📍 Рыболовные места'],
            ['🐟 Поиск по рыбе', '📊 Отчеты'],
            ['📋 Помощь']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        welcome_text = f"""
👋 Привет, {user.first_name}! Я твой рыболовный помощник!

🌤 *Что я умею:*
• Показывать погоду и прогноз клёва
• Находить рыболовные места
• Искать места по виду рыбы
• Показывать свежие отчеты

🎯 *Просто нажми нужную кнопку ниже!*

📍 *Примеры использования:*
• Нажми «🎣 Погода и клёв» → введи «Москва»
• Нажми «🐟 Поиск по рыбе» → введи «щука»
• Нажми «📍 Рыболовные места» → введи «СПб»
        """
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def send_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать справку"""
        help_text = """
🎣 *SpinFM Рус - Рыболовный помощник*

*Основные команды:*
/start - начать работу
/weather [город] - погода и клёв
/spots [город] - рыболовные места  
/fish [вид рыбы] - места для ловли
/reports - последние отчеты
/help - эта справка

*Как использовать:*
1. Используйте кнопки ниже для быстрого доступа
2. Или вводите команды вручную
3. Для погоды - просто введите название города

*Примеры запросов:*
• `Москва` - погода в Москве
• `/spots СПб` - места в Санкт-Петербурге
• `/fish щука` - места для ловли щуки

*Поддерживаемые города:*
Россия, Украина, Беларусь, Европа, США, Азия
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
            
            if response.status_code == 404:
                logger.warning(f"Город не найден: {city}")
                return None
            elif response.status_code != 200:
                logger.error(f"Weather API error: {response.status_code} - {response.text}")
                return None

            data = response.json()
            
            # Проверяем, что город найден
            if data.get('cod') != 200:
                logger.warning(f"Город не найден в ответе API: {city}")
                return None
                
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
            logger.error(f"Error getting weather for {city}: {e}")
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
        city = update.message.text.strip()
        
        if not city or len(city) < 2:
            await update.message.reply_text("🌤 Введите название города (минимум 2 символа)")
            return

        await update.message.reply_chat_action(action='typing')

        # Получаем данные о погоде
        weather_data = self.get_weather(city)
        
        if not weather_data:
            # Попробуем найти похожие города или дадим подсказки
            suggestions = {
                'москва': 'Москва', 'спб': 'Санкт-Петербург', 'питер': 'Санкт-Петербург',
                'киев': 'Киев', 'минск': 'Минск', 'казань': 'Казань', 'новосибирск': 'Новосибирск'
            }
            
            suggestion = suggestions.get(city.lower())
            if suggestion:
                await update.message.reply_text(
                    f"Возможно вы имели в виду *{suggestion}*?\n"
                    f"Попробуйте отправить: {suggestion}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Не удалось найти погоду для этого города.\n\n"
                    "🔍 *Проверьте:*\n"
                    "• Правильность написания\n"
                    "• Попробуйте английское название\n"
                    "• Используйте крупные города\n\n"
                    "🌆 *Примеры работающих городов:*\n"
                    "• Москва, СПб, Киев, Минск\n"
                    "• Лондон, Берлин, Париж\n"
                    "• Нью-Йорк, Токио, Пекин",
                    parse_mode='Markdown'
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
        """Показать рыболовные места в городе - КОМАНДА"""
        city = ' '.join(context.args) if context.args else None
        
        if not city:
            # Если город не указан, просим ввести
            await update.message.reply_text(
                "🗺️ *Поиск рыболовных мест*\n\n"
                "Введите название города после команды:\n"
                "`/spots Москва`\n"
                "`/spots Санкт-Петербург`\n"
                "`/spots Новосибирск`\n\n"
                "Или используйте кнопку «📍 Рыболовные места»",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_chat_action(action='typing')
        
        spots = fishing_db.get_spots_by_city(city.lower())
        
        if not spots:
            await update.message.reply_text(
                f"❌ Не найдено рыболовных мест в городе *{city}*\n\n"
                f"📌 *Попробуйте эти города:*\n"
                f"• Москва\n• Санкт-Петербург\n• Новосибирск\n• Екатеринбург\n\n"
                f"🌍 *Или введите другой крупный город*",
                parse_mode='Markdown'
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
        
        await update.message.reply_text(message, parse_mode='Markdown')

    async def search_spots_by_fish(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поиск мест по виду рыбы - КОМАНДА"""
        fish_species = ' '.join(context.args) if context.args else None
        
        if not fish_species:
            await update.message.reply_text(
                "🎣 *Поиск мест по виду рыбы*\n\n"
                "Введите вид рыбы после команды:\n"
                "`/fish щука`\n"
                "`/fish карп`\n"
                "`/fish окунь`\n"
                "`/fish лещ`\n"
                "`/fish судак`\n\n"
                "Или используйте кнопку «🐟 Поиск по рыбе»",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_chat_action(action='typing')
        
        spots = fishing_db.get_spots_by_fish(fish_species.lower())
        
        if not spots:
            await update.message.reply_text(
                f"❌ Не найдено мест для ловли *{fish_species}*\n\n"
                f"🐟 *Попробуйте эти виды рыб:*\n"
                f"• щука\n• карп\n• окунь\n• лещ\n• судак\n• плотва\n\n"
                f"📍 *Или проверьте другие города в базе*",
                parse_mode='Markdown'
            )
            return
        
        message = f"🎣 *Места для ловли {fish_species.title()}*\n\n"
        
        # Группируем по городам
        cities = {}
        for spot in spots:
            if spot['city'] not in cities:
                cities[spot['city']] = []
            cities[spot['city']].append(spot)
        
        for city, city_spots in list(cities.items())[:3]:  # Ограничиваем 3 городами
            message += f"🏙️ *{city.title()}*\n"
            for spot in city_spots[:2]:  # Ограничиваем 2 местами на город
                message += f"• *{spot['name']}* - {spot['description']}\n"
            message += "\n"
        
        message += f"🔍 *Найдено всего: {len(spots)} мест*"
        
        await update.message.reply_text(message, parse_mode='Markdown')

    async def show_recent_reports(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать последние отчеты о рыбалке"""
        reports = fishing_db.get_recent_reports(limit=5)
        
        if not reports:
            await update.message.reply_text(
                "📊 *Пока нет отчетов о рыбалке*\n\n"
                "Будьте первым, кто добавит отчет о своей рыбалке!",
                parse_mode='Markdown'
            )
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
        text = update.message.text.strip()
        
        if text == '📋 Помощь':
            await self.send_help(update, context)
        elif text == '🎣 Погода и клёв':
            await update.message.reply_text(
                "🌤 *Отправьте название города:*\n\n"
                "Примеры:\n• Москва\n• Санкт-Петербург\n• Киев\n• Лондон\n• Берлин",
                parse_mode='Markdown'
            )
        elif text == '📍 Рыболовные места':
            await update.message.reply_text(
                "🗺️ *Введите название города для поиска мест:*\n\n"
                "Примеры:\n• Москва\n• СПб\n• Новосибирск\n• Екатеринбург",
                parse_mode='Markdown'
            )
        elif text == '🐟 Поиск по рыбе':
            await update.message.reply_text(
                "🎣 *Введите вид рыбы для поиска:*\n\n"
                "Примеры:\n• щука\n• карп\n• окунь\n• лещ\n• судак",
                parse_mode='Markdown'
            )
        elif text == '📊 Отчеты':
            await self.show_recent_reports(update, context)
        else:
            # Если просто текст - проверяем, что это не команда для других функций
            lower_text = text.lower()
            
            # Если ввели название рыбы - предлагаем использовать поиск по рыбе
            fish_keywords = ['щука', 'карп', 'окунь', 'лещ', 'судак', 'плотва', 'карась', 'линь']
            if any(fish in lower_text for fish in fish_keywords):
                await update.message.reply_text(
                    f"🎣 *Для поиска мест по рыбе используйте:*\n\n"
                    f"Кнопку «🐟 Поиск по рыбе» или команду:\n`/fish {text}`",
                    parse_mode='Markdown'
                )
                return
            
            # Если ввели короткий текст (возможно город для мест)
            elif len(text) < 10 and not any(char.isdigit() for char in text):
                # Предлагаем оба варианта
                await update.message.reply_text(
                    f"🔍 *Что вы хотите найти?*\n\n"
                    f"Если это город для погоды - просто отправьте его\n"
                    f"Если это город для поиска мест - используйте:\n`/spots {text}`\n\n"
                    f"Или выберите нужную кнопку ниже 👇",
                    parse_mode='Markdown'
                )
                return
            
            # Иначе считаем это запросом погоды
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
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
