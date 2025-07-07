# Weather Telegram Bot

Telegram бот для получения информации о погоде в любом городе мира.

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Настройте переменные окружения:

### Для Windows (PowerShell):
```powershell
$env:BOT_TOKEN="ваш_токен_бота_от_botfather"
$env:OPENWEATHER_API_KEY="ваш_api_ключ_openweathermap"
```

### Для Windows (Command Prompt):
```cmd
set BOT_TOKEN=ваш_токен_бота_от_botfather
set OPENWEATHER_API_KEY=ваш_api_ключ_openweathermap
```

### Для Linux/Mac:
```bash
export BOT_TOKEN="ваш_токен_бота_от_botfather"
export OPENWEATHER_API_KEY="ваш_api_ключ_openweathermap"
```

## Получение API ключей

### Telegram Bot Token
1. Найдите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен

### OpenWeatherMap API Key
1. Зарегистрируйтесь на [OpenWeatherMap](https://openweathermap.org/)
2. Перейдите в раздел API Keys
3. Скопируйте ваш API ключ

## Запуск

```bash
python main.py
```

## Использование

1. Найдите вашего бота в Telegram
2. Отправьте команду `/start`
3. Отправьте название города для получения информации о погоде

## Команды

- `/start` - Начать работу с ботом
- `/help` - Получить справку 