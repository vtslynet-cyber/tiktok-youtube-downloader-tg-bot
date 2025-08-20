# Телеграмм бот для скачки видео из TikTok, YouTube Shorts и Reels.

![Логотип бота](https://github.com/vtslynet-cyber/tiktok-youtube-downloader-tg-bot/blob/main/logobot.png)

Этот бот позволяет скачивать видео без водяных знаков из TikTok, YouTube Shorts и Instagram.

## Возможности
v1.0.0
- Скачивание видео из TikTok, YouTube Shorts и Instagram.
- Автоматическое определение платформы.
- Ограничение по размеру файлов (до 50MB).
- Логирование всех действий (`bot.log`).
- Хранение списка пользователей (`users.txt`).
- Ведение статистики скачиваний (`stats.txt`).
- Список обязательных каналов для подписки (`channels.txt`).


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

## Instagram и cookies

Для скачивания Instagram Reels/Stories иногда требуется авторизация.  
Чтобы бот корректно скачивал такие видео, нужно использовать cookies-файл.

1. Авторизуйтесь в Instagram через браузер (Chrome/Firefox).
2. Сохраните cookies (например, через расширение [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg)).
3. Сохраните файл как `cookies.txt`.
4. Переместите его на сервер в папку с ботом.

## Зависимости
Список зависимостей — в `requirements.txt`.

## v1.1.0

- Добавлена проверка подписки на канал(ы)
- Управление обязательной подпиской через админку
- Кнопка «Подписаться» для новых пользователей

## v1.0.0

- Первая рабочая версия (скачивание TikTok / YouTube Shorts / Instagram)
- Админ-панель (рассылка, статистика)

### Проверить бота👉https://t.me/vtslysave_bot

