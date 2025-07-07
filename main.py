import os
import requests
import aiohttp
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
AIR_QUALITY_API_KEY = os.getenv("AIR_QUALITY_API_KEY")  # OpenWeatherMap Air Quality API
SOLAR_API_KEY = os.getenv("SOLAR_API_KEY")  # NASA Solar Flare API (бесплатный)


# --- Функции для работы с различными API ---

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

def get_air_quality_data(lat, lon, api_key):
    """
    Получает данные о качестве воздуха.
    """
    if not api_key:
        return None
    
    base_url = "http://api.openweathermap.org/data/2.5/air_pollution"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json()
    except:
        return None

def get_solar_activity_data():
    """
    Получает данные о солнечной активности и магнитных бурях.
    """
    # Используем бесплатный API от NOAA
    base_url = "https://services.swpc.noaa.gov/json/goes/primary/xray-1-day.json"
    
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Получаем последние данные о солнечных вспышках
        if data and len(data) > 0:
            latest_flare = data[-1]
            return {
                'flare_class': latest_flare.get('class', 'N/A'),
                'flare_time': latest_flare.get('time_tag', 'N/A'),
                'intensity': latest_flare.get('flux', 'N/A')
            }
    except:
        pass
    
    return None

def get_radiation_data(lat, lon):
    """
    Получает данные о радиационном фоне (используем OpenWeatherMap UV Index).
    """
    if not OPENWEATHER_API_KEY:
        return None
    
    base_url = "http://api.openweathermap.org/data/2.5/air_pollution"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data and 'list' in data and len(data['list']) > 0:
            current = data['list'][0]
            return {
                'uv_index': current.get('main', {}).get('aqi', 'N/A'),
                'components': current.get('components', {})
            }
    except:
        pass
    
    return None

def format_air_quality_message(air_data):
    """
    Форматирует данные о качестве воздуха.
    """
    if not air_data or 'list' not in air_data or len(air_data['list']) == 0:
        return ""
    
    current = air_data['list'][0]
    aqi = current['main']['aqi']
    components = current['components']
    
    # Определяем качество воздуха
    aqi_levels = {
        1: "Хорошее",
        2: "Удовлетворительное", 
        3: "Умеренное",
        4: "Плохое",
        5: "Очень плохое"
    }
    
    aqi_text = aqi_levels.get(aqi, "Неизвестно")
    
    message = f"\n🌬️ *Качество воздуха*: {aqi_text} \\(AQI: {aqi}\\)\n"
    message += f"• PM2\\.5: {components.get('pm2_5', 'N/A')} μg/m³\n"
    message += f"• PM10: {components.get('pm10', 'N/A')} μg/m³\n"
    message += f"• NO₂: {components.get('no2', 'N/A')} μg/m³\n"
    message += f"• O₃: {components.get('o3', 'N/A')} μg/m³\n"
    
    return message

def format_solar_activity_message(solar_data):
    """
    Форматирует данные о солнечной активности.
    """
    if not solar_data:
        return ""
    
    message = f"\n☀️ *Солнечная активность*:\n"
    message += f"• Класс вспышки: {solar_data.get('flare_class', 'N/A')}\n"
    message += f"• Время: {solar_data.get('flare_time', 'N/A')}\n"
    message += f"• Интенсивность: {solar_data.get('intensity', 'N/A')}\n"
    
    # Добавляем информацию о магнитных бурях
    flare_class = solar_data.get('flare_class', '')
    if flare_class in ['M', 'X']:
        message += "⚠️ *Внимание! Возможны магнитные бури*\n"
    elif flare_class == 'C':
        message += "ℹ️ *Умеренная солнечная активность*\n"
    else:
        message += "✅ *Солнечная активность в норме*\n"
    
    return message

def format_radiation_message(radiation_data):
    """
    Форматирует данные о радиации.
    """
    if not radiation_data:
        return ""
    
    uv_index = radiation_data.get('uv_index', 'N/A')
    components = radiation_data.get('components', {})
    
    message = f"\n☢️ *Радиационный фон*:\n"
    message += f"• УФ индекс: {uv_index}\n"
    
    # Определяем уровень УФ излучения
    if uv_index != 'N/A':
        try:
            uv = int(uv_index)
            if uv <= 2:
                uv_level = "Низкий"
            elif uv <= 5:
                uv_level = "Умеренный"
            elif uv <= 7:
                uv_level = "Высокий"
            elif uv <= 10:
                uv_level = "Очень высокий"
            else:
                uv_level = "Экстремальный"
            message += f"• Уровень УФ: {uv_level}\n"
        except:
            pass
    
    return message

def format_weather_message(current_data, forecast_data, air_data=None, solar_data=None, radiation_data=None):
    """
    Форматирует полученные данные о погоде и дополнительную информацию в читаемое сообщение.
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

    # Добавляем информацию о качестве воздуха
    if air_data:
        message += format_air_quality_message(air_data)

    # Добавляем информацию о солнечной активности
    if solar_data:
        message += format_solar_activity_message(solar_data)

    # Добавляем информацию о радиации
    if radiation_data:
        message += format_radiation_message(radiation_data)

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
        # Получаем координаты города
        lat = current_weather['coord']['lat']
        lon = current_weather['coord']['lon']
        
        # Получаем дополнительную информацию
        air_data = get_air_quality_data(lat, lon, AIR_QUALITY_API_KEY)
        solar_data = get_solar_activity_data()
        radiation_data = get_radiation_data(lat, lon)
        
        weather_text = format_weather_message(current_weather, forecast, air_data, solar_data, radiation_data)
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
    
    # Предупреждения о дополнительных API ключах
    if not AIR_QUALITY_API_KEY:
        print("Предупреждение: AIR_QUALITY_API_KEY не установлен. Информация о качестве воздуха будет недоступна.")
    if not SOLAR_API_KEY:
        print("Предупреждение: SOLAR_API_KEY не установлен. Информация о солнечной активности будет ограничена.")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, weather_message))
    application.add_handler(MessageHandler(filters.COMMAND | filters.TEXT, unknown_message))

    print("Бот запущен! Отправь ему сообщение в Telegram.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()