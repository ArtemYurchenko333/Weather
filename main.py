import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


# --- Функции для работы с OpenWeatherMap ---

def escape_markdown(text):
    """
    Экранирует специальные символы для Telegram Markdown V2.
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def get_weather_data(city_name, api_key):
    """
    Получает данные о текущей погоде и 5-дневный прогноз для указанного города.
    """
    base_url_current = "http://api.openweathermap.org/data/2.5/weather?"
    base_url_forecast = "http://api.openweathermap.org/data/2.5/forecast?"

    params_current = {
        "q": city_name,
        "appid": api_key,
        "units": "metric",  # Метрические единицы (Цельсий)
        "lang": "ru"        # Русский язык
    }

    params_forecast = {
        "q": city_name,
        "appid": api_key,
        "units": "metric",  # Метрические единицы (Цельсий)
        "lang": "ru"        # Русский язык
    }

    current_weather_data = None
    forecast_data = None

    try:
        response_current = requests.get(base_url_current, params=params_current)
        response_current.raise_for_status()
        current_weather_data = response_current.json()

        response_forecast = requests.get(base_url_forecast, params=params_forecast)
        response_forecast.raise_for_status()
        forecast_data = response_forecast.json()

    except requests.exceptions.HTTPError as http_err:
        if response_current.status_code == 404 or response_forecast.status_code == 404:
            return None, "Город не найден. Пожалуйста, проверьте название города."
        return None, f"Ошибка HTTP: {http_err}"
    except requests.exceptions.ConnectionError as conn_err:
        return None, f"Ошибка подключения: {conn_err}. Проверьте ваше интернет-соединение."
    except requests.exceptions.Timeout as timeout_err:
        return None, f"Превышено время ожидания: {timeout_err}."
    except requests.exceptions.RequestException as req_err:
        return None, f"Произошла непредвиденная ошибка: {req_err}."

    return current_weather_data, forecast_data

def format_weather_message(current_data, forecast_data):
    """
    Форматирует полученные данные о погоде в читаемое сообщение.
    """
    if not current_data:
        return "Не удалось получить данные о погоде."

    city_name = current_data['name']
    country = current_data['sys']['country']
    temp = current_data['main']['temp']
    feels_like = current_data['main']['feels_like']
    description = current_data['weather'][0]['description']
    humidity = current_data['main']['humidity']
    wind_speed = current_data['wind']['speed']
    rain = current_data.get('rain', {}).get('1h', 0) if current_data.get('rain') else 0
    snow = current_data.get('snow', {}).get('1h', 0) if current_data.get('snow') else 0

    message = (
        f"Погода в *{city_name}, {country}*:\n"
        f"🌡️ *Температура*: {temp:.1f}°C (ощущается как {feels_like:.1f}°C)\n"
        f"☁️ *Описание*: {description.capitalize()}\n"
        f"💧 *Влажность*: {humidity}%\n"
        f"💨 *Скорость ветра*: {wind_speed:.1f} м/с\n"
    )
    if rain > 0:
        message += f"🌧️ *Осадки (дождь за 1 час)*: {rain} мм\n"
    if snow > 0:
        message += f"🌨️ *Осадки (снег за 1 час)*: {snow} мм\n"

    if forecast_data and forecast_data.get('list'):
        message += "\n*Прогноз на ближайшее время:*\n"
        
        forecast_by_day = {}
        for item in forecast_data['list']:
            date = item['dt_txt'].split(' ')[0] 
            if date not in forecast_by_day:
                forecast_by_day[date] = item
                if len(forecast_by_day) >= 3: 
                    break

        for date, item in forecast_by_day.items():
            temp_min = item['main']['temp_min']
            temp_max = item['main']['temp_max']
            description_forecast = item['weather'][0]['description']
            message += (
                f"🗓️ *{date}*: {description_forecast.capitalize()}, "
                f"темп. от {temp_min:.1f}°C до {temp_max:.1f}°C\n"
            )

    # Экранируем весь текст после форматирования
    return escape_markdown(message)

# --- Функции-обработчики для Telegram бота ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start."""
    await update.message.reply_text('Привет! Я бот, который покажет тебе погоду. Просто напиши название города!')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /help."""
    await update.message.reply_text('Чтобы узнать погоду, просто отправь мне название города (например, "Киев" или "London").')

async def weather_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения от пользователя (название города)."""
    city_name = update.message.text
    
    if not OPENWEATHER_API_KEY:
        await update.message.reply_text("Ошибка: API ключ OpenWeatherMap не настроен. Пожалуйста, свяжитесь с администратором бота.")
        return

    await update.message.reply_text(f"Ищу погоду в городе {city_name}...")
    
    current_weather, forecast = get_weather_data(city_name, OPENWEATHER_API_KEY)

    if current_weather:
        weather_text = format_weather_message(current_weather, forecast)
        await update.message.reply_markdown_v2(weather_text)
    else:
        await update.message.reply_text(forecast or "Не удалось получить данные о погоде для этого города.")


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отвечает на неизвестные команды или сообщения."""
    await update.message.reply_text("Извини, я не понимаю эту команду. Попробуй отправить название города или используй /help.")

def main():
    """Запускает бота."""
    if not TELEGRAM_BOT_TOKEN:
        print("Ошибка: Переменная окружения BOT_TOKEN не установлена. Пожалуйста, установите токен бота из BotFather.")
        return
    if not OPENWEATHER_API_KEY:
        print("Ошибка: Переменная окружения OPENWEATHER_API_KEY не установлена. Пожалуйста, установите API ключ OpenWeatherMap.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, weather_message))
    application.add_handler(MessageHandler(filters.COMMAND | filters.TEXT, unknown_message))

    print("Бот запущен! Отправь ему сообщение в Telegram.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()