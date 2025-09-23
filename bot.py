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
WEBHOOK_URL = os.getenv('WEBHOOK_URL', "https://spin-fm-bot-pgjh.onrender.com")

WEATHER_API_URL_TODAY = "http://api.openweathermap.org/data/2.5/weather"
WEATHER_API_URL_FORECAST = "http://api.openweathermap.org/data/2.5/forecast"

def hpa_to_mmhg(hpa):
    """Конвертирует гектопаскали в миллиметры ртутного столба."""
    return hpa * 0.750062

class FishingBot:
    def __init__(self):
        self.weather_cache = {}
        self.cache_timeout = 1800

    def get_weather_data(self, city, url_type='forecast'):
        """Получение прогноза погоды."""
        try:
            params = {
                'q': city,
                'appid': WEATHER_API_KEY,
                'units': 'metric',
                'lang': 'ru'
            }
            api_url = WEATHER_API_URL_FORECAST if url_type == 'forecast' else WEATHER_API_URL_TODAY
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса к API погоды: {e}")
            return None

    def calculate_fishing_conditions(self, temp, pressure, wind_speed):
        """
        Прогнозирование клёва на основе погоды с тремя простыми советами.
        """
        score = 0
        
        # Влияние температуры
        if 10 <= temp <= 20:
            score += 2
        elif temp > 20:
            score += 1
        else:
            score -= 1

        # Влияние давления (нормальное давление ~760 мм рт. ст.)
        pressure_mmhg = hpa_to_mmhg(pressure)
        if 755 <= pressure_mmhg <= 765:
            score += 2
        elif pressure_mmhg < 755:
            score += 1
        else:
            score -= 1

        # Влияние ветра
        if wind_speed < 5:
            score += 2
        elif wind_speed >= 5:
            score += 1

        # Определение иконки и единого совета на основе очков
        if score >= 4:
            icon = "🟢"
            advice = "Клевать будет так, что клиент позабудет обо всём на свете! *Бриллиантовая рука."
        elif score >= 2:
            icon = "🟡"
            advice = "Если очень хочется и делать все равно нечего, то можно и порыбачить."
        else:
            icon = "🔴"
            advice = "Лучше остаться дома и посмотреть сериальчик😜"
            
        return icon, advice

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        keyboard = [
            [KeyboardButton('🎣 Прогноз на сегодня')],
            [KeyboardButton('🎣 Прогноз на 5 дней')],
            [KeyboardButton('📊 Помощь')]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        welcome_text = f"""
👋 Привет, {user.first_name}! Я твой рыболовный помощник!
🌤 Я могу показать погоду в любом городе и спрогнозировать клёв рыбы.
🎯 Просто выбери нужную кнопку, и я пришлю тебе прогноз!
"""
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        logger.info(f"Команда /start выполнена для пользователя {user.first_name}")

    async def send_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка справочной информации"""
        help_text = """
Помощь по боту:
* Нажми кнопку "**Прогноз на сегодня**" или "**Прогноз на 5 дней**".
* Введи название города, когда я попрошу.
* Используй команду /start, чтобы перезапустить бота и снова увидеть кнопки.
"""
        await update.message.reply_text(help_text)

    async def prompt_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет запрос на ввод города и сохраняет тип прогноза в контекст."""
        button_text = update.message.text
        if button_text == '🎣 Прогноз на сегодня':
            context.user_data['forecast_type'] = 'today'
        elif button_text == '🎣 Прогноз на 5 дней':
            context.user_data['forecast_type'] = 'forecast'
        
        await update.message.reply_text("Отлично! Теперь введи название города, для которого нужно сделать прогноз.")

    async def handle_city_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает введенное название города и отправляет прогноз."""
        city = update.message.text
        forecast_type = context.user_data.get('forecast_type')

        if not forecast_type:
            await update.message.reply_text("Пожалуйста, сначала выбери тип прогноза, нажав на одну из кнопок.")
            return
            
        await update.message.reply_text(f"Ищу прогноз для города **{city}**...")
        
        weather_data = self.get_weather_data(city, url_type=forecast_type)
        
        if not weather_data:
            await update.message.reply_text("Не могу найти такой город. Попробуйте еще раз.")
            return

        if forecast_type == 'today':
            main_data = weather_data['main']
            wind_speed = weather_data['wind']['speed']
            clouds = weather_data['clouds']['all']
            pressure_mmhg = hpa_to_mmhg(main_data['pressure'])

            fishing_icon, fishing_advice = self.calculate_fishing_conditions(
                main_data['temp'],
                main_data['pressure'],
                wind_speed
            )
            
            forecast_text = f"**Прогноз на сегодня для {city.capitalize()}:**\n"
            forecast_text += f"🌡️ **Температура**: {main_data['temp']:.1f}°C\n"
            forecast_text += f"🌬️ **Ветер**: {wind_speed:.1f} м/с\n"
            forecast_text += f"💧 **Влажность**: {main_data['humidity']}%\n"
            forecast_text += f"📉 **Давление**: {pressure_mmhg:.1f} мм рт. ст.\n"
            forecast_text += f"🐟 **Клёв**: **{fishing_icon} {fishing_advice}**"

        else: # forecast_type == 'forecast'
            forecast_text = f"Прогноз клёва и погоды на 5 дней для города **{city.capitalize()}**:\n\n"
            
            current_hour = datetime.now().hour
            if 5 <= current_hour < 10 or 17 <= current_hour < 22:
                forecast_text += "✨ **Сейчас лучшее время для рыбалки! Утренний и вечерний клёв самые активные.**\n\n"
            
            for item in weather_data['list'][::8]:
                date_time = datetime.fromtimestamp(item['dt'])
                main_data = item['main']
                wind_speed = item['wind']['speed']
                clouds = item['clouds']['all']
                pressure_mmhg = hpa_to_mmhg(main_data['pressure'])
                
                fishing_icon, fishing_advice = self.calculate_fishing_conditions(
                    main_data['temp'],
                    main_data['pressure'],
                    wind_speed
                )
                
                forecast_text += f"**{date_time.strftime('%A, %d %B')}**\n"
                forecast_text += f"🌡️ **Температура**: {main_data['temp']:.1f}°C, ощущается как {main_data['feels_like']:.1f}°C\n"
                forecast_text += f"🌬️ **Ветер**: {wind_speed:.1f} м/с\n"
                forecast_text += f"☁️ **Облачность**: {clouds}%\n"
                forecast_text += f"💧 **Влажность**: {main_data['humidity']}%\n"
                forecast_text += f"📉 **Давление**: {pressure_mmhg:.1f} мм рт. ст.\n"
                forecast_text += f"🐟 **Клёв**: **{fishing_icon} {fishing_advice}**\n"
                forecast_text += "––––––––––––––––––––\n"
            
        await update.message.reply_text(forecast_text)
        context.user_data.pop('forecast_type', None)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}")
        if update and update.message:
            await update.message.reply_text("⚠️ Произошла ошибка. Попробуйте позже.")

def main():
    """Основная функция, переделанная под вебхук."""
    logger.info("Запуск бота как веб-сервиса...")
    
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

    application.add_handler(CommandHandler("start", fishing_bot.start))
    application.add_handler(CommandHandler("help", fishing_bot.send_help))
    
    application.add_handler(MessageHandler(filters.Regex('^🎣 Прогноз на сегодня$'), fishing_bot.prompt_city))
    application.add_handler(MessageHandler(filters.Regex('^🎣 Прогноз на 5 дней$'), fishing_bot.prompt_city))
    application.add_handler(MessageHandler(filters.Regex('^📊 Помощь$'), fishing_bot.send_help))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fishing_bot.handle_city_input))

    application.add_error_handler(fishing_bot.error_handler)

    port = int(os.environ.get('PORT', 8080))
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == '__main__':
    main()
