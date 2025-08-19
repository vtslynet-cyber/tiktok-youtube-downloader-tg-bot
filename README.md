# Телеграмм бот для скачки видео из TikTok, YouTube Shorts и Reels.

![Логотип бота](https://github.com/vtslynet-cyber/tiktok-youtube-downloader-tg-bot/blob/main/logobot.png)

Этот бот позволяет скачивать видео без водяных знаков из TikTok, YouTube Shorts и Instagram.

## Возможности
- Скачивание видео из TikTok, YouTube Shorts и Instagram.
- Автоматическое определение платформы.
- Ограничение по размеру файлов (до 50MB).
- Логирование всех действий (`bot.log`).
- Хранение списка пользователей (`users.txt`).
- Ведение статистики скачиваний (`stats.txt`).
- Админ-панель:
  - 📢 Рассылка сообщений пользователям.
  - 📢 Рассылка сообщений с кнопкой.
  - 📊 Просмотр статистики.

## Запуск
## Настройка
Перед запуском необходимо:

1. Получить токен у [BotFather](https://t.me/BotFather) и прописать его в коде:
   ```python
   TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"
   ADMIN_ID = ВАШ_ID
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Запустите бота:
   ```bash
   python bot.py
   ```

## Зависимости
Список зависимостей — в `requirements.txt`.

# UDP‼️Сторис из Inst на данный момент не поддерживает. 
