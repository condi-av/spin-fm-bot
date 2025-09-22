import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
import math

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация с вашими токенами
BOT_TOKEN = os.getenv('BOT_TOKEN', "8199190847:AAFFnG2fYEd3Zurne8yP1alevSsSeKh5VRk")
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', "d192e284d050cbe679c3641f372e7a02")
WEATHER_API_URL_FORECAST = "http://api.openweathermap.org/data/2.5/forecast"

class FishingBot:
    def __init__(self):
        self.weather_cache = {}
        self.cache_timeout = 1800  # 30 минут

    def get_weather_data(self, city):
        """Получение прогноза погоды на 5 дней."""
        try:
            params = {
                'q': city,
                'appid': WEATHER_API_KEY,
                'units': 'metric',
                'lang': 'ru'
            }
            response = requests.get(WEATHER_API_URL_FORECAST, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса к API погоды: {e}")
            return None

    def calculate_fishing_conditions(self, temp, pressure, wind_speed, clouds):
        """
        Прогнозирование клёва на основе погоды.
        Усовершенствованная версия.
        """
        score = 0
        advice = ""
        
        # Влияние температуры
        if 10 <= temp <= 20:
            score += 2
            advice += "Температура отличная для большинства видов рыб. "
        elif temp > 20:
            score += 1
            advice += "В тёплой воде рыба может быть менее активна, ищите её на глубине. "
        else:
            score -= 1
            advice += "Вода холодная, клёв может быть медленным. "

        # Влияние давления
        if 1010 <= pressure <= 1020:
            score += 2
            advice += "Давление стабильное, рыба должна быть активна. "
        elif pressure < 1010:
            score += 1
            advice += "Давление падает – клёв должен быть хороший. "
        else:
            score -= 1
            advice += "Высокое давление, рыба может быть менее активна. "

        # Влияние ветра и облачности
        if wind_speed < 5 and clouds < 50:
            score += 2
            advice += "Тихая, ясная погода. Отлично для поплавочной рыбалки. "
        elif wind_speed >= 5:
            score += 1
            advice += "Небольшой ветер рябит воду, что хорошо для хищника. "
        else:
            advice += "Сильный ветер, клёв может быть сложным. "

        # Определение иконки на основе очков
        if score >= 4:
            icon = "🟢"  # Отличный клёв
        elif score >= 2:
            icon = "🟡"  # Средний клёв
        else:
            icon = "🔴"  # Плохой клёв
            
        return icon, advice

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        keyboard = [
            [KeyboardButton('🎣 Прогноз на 5 дней')],
            [KeyboardButton('📊 Помощь')]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        welcome_text = f"""
👋 Привет, {user.first_name}! Я твой рыболовный помощник!

🌤 Я могу показать погоду в любом городе и спрогнозировать клёв рыбы на 5 дней.

🎯 Просто нажми кнопку «🎣 Прогноз на 5 дней» и отправь мне название города!
"""
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        logger.info(f"Команда /start выполнена для пользователя {user.first_name}")

    async def send_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка справочной информации"""
        help_text = """
Помощь по боту:
* Просто отправь мне название города, и я пришлю прогноз погоды и клёва на 5 дней.
* Используй команду /start, чтобы перезапустить бота.
* Используй команду /help, чтобы увидеть это сообщение снова.
"""
        await update.message.reply_text(help_text)

    async def handle_weather_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик запроса погоды и клёва"""
        await update.message.reply_text("Пожалуйста, отправьте мне название города.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений (названия городов)"""
        city = update.message.text
        await update.message.reply_text(f"Ищу прогноз для города {city}...")
        
        weather_data = self.get_weather_data(city)
        
        if not weather_data:
            await update.message.reply_text("Не могу найти такой город. Попробуйте еще раз.")
            return

        forecast_text = f"Прогноз клёва и погоды на 5 дней для города {city.capitalize()}:\n\n"
        
        # Получение фазы луны (примерно, так как OneCall API не используется)
        # Для получения точных фаз луны, нужно использовать другой эндпоинт, 
        # но для демонстрации можно взять из daily forecast.
        # В этом API нет moon_phase, поэтому мы дадим общий совет, основанный на времени суток
        current_hour = datetime.now().hour
        if 5 <= current_hour < 10 or 17 <= current_hour < 22:
            forecast_text += "✨ Сейчас лучшее время для рыбалки! Утренний и вечерний клёв самые активные.\n\n"
        
        # Проходим по списку прогнозов
        for item in weather_data['list'][::8]:  # Каждые 8 элементов = 1 день
            date_time = datetime.fromtimestamp(item['dt'])
            main_data = item['main']
            weather_desc = item['weather'][0]['description']
            wind_speed = item['wind']['speed']
            clouds = item['clouds']['all']
            
            # Прогноз клёва
            fishing_icon, fishing_advice = self.calculate_fishing_conditions(
                main_data['temp'],
                main_data['pressure'],
                wind_speed,
                clouds
            )
            
            forecast_text += f"**{date_time.strftime('%A, %d %B')}**\n"
            forecast_text += f"🌡️ Температура: {main_data['temp']:.1f}°C, ощущается как {main_data['feels_like']:.1f}°C\n"
            forecast_text += f"🌬️ Ветер: {wind_speed:.1f} м/с\n"
            forecast_text += f"☁️ Облачность: {clouds}%\n"
            forecast_text += f"💧 Влажность: {main_data['humidity']}%\n"
            forecast_text += f"📉 Давление: {main_data['pressure']} hPa\n"
            forecast_text += f"🐟 Клёв: **{fishing_icon} {fishing_advice}**\n"
            forecast_text += "––––––––––––––––––––\n"
            
        await update.message.reply_text(forecast_text)

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fishing_bot.handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(fishing_bot.error_handler)

    # Запуск бота (без polling)
    # application.run_polling(poll_interval=1)
    application.run_polling()
