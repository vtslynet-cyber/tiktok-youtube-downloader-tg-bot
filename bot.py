import os
import re
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)
from telegram.error import NetworkError, TimedOut, Forbidden

TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER" #Токен tg
ADMIN_ID = ВАШ_ID   #Aдмин ID

#Файлы Если будете ставить на сервер <указывайте точный путь до файлов>
USERS_FILE = "users.txt" #Хранение списка пользователей
LOG_FILE = "bot.log" #Логирование всех действий
STATS_FILE = "stats.txt" #Ведение статистики скачиваний

last_request_time = {}

def write_log(message: str):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return f.read().splitlines()

def save_user(user_id: int, username: str | None):
    record = f"{user_id} ({username})"
    users = load_users()
    if record not in users:
        with open(USERS_FILE, "a", encoding="utf-8") as f:
            f.write(record + "\n")

def remove_user(user_id: int):
    users = load_users()
    new_users = [u for u in users if not u.startswith(str(user_id))]
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(new_users))

def update_stats(user_id: int, username: str | None):
    stats = {}
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                uid, count = line.strip().split(":", 1)
                stats[uid] = int(count)

    key = f"{user_id} ({username})"
    stats[key] = stats.get(key, 0) + 1

    with open(STATS_FILE, "w", encoding="utf-8") as f:
        for k, v in stats.items():
            f.write(f"{k}:{v}\n")

#/start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.username)
    write_log(f"Пользователь {user.id} ({user.username}) нажал /start")

    keyboard = [[InlineKeyboardButton("🔥 Поддержать проект и купить ключ", url="https://t.me/VTSLYVPN_bot")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Привет! Отправь мне ссылку на видео (TikTok, YouTube Shorts, Instagram Reels/посты/сторисы), "
        "и я скачаю его без водяных знаков.",
        reply_markup=reply_markup
    )

#yt_dlp model
async def run_yt_dlp(url: str) -> str | None:
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp", url,
        "--max-filesize", "49M",
        "--no-playlist",
        "--no-continue",
        "--retries", "3",
        "--http-chunk-size", "5M",
        "--restrict-filenames",
        "-f", "mp4/best",
        "-o", "downloaded_video.%(ext)s",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        proc.kill()
        write_log("[ERROR] yt-dlp timeout (превышено время ожидания)")
        return None

    out = stdout.decode("utf-8", errors="ignore")
    err = stderr.decode("utf-8", errors="ignore")

    write_log(f"yt-dlp stdout:\n{out}")
    if err.strip():
        write_log(f"yt-dlp stderr:\n{err}")

    match = re.search(r"\[download\] Destination: (.+)", out)
    if match:
        filename = match.group(1).strip()
        if os.path.exists(filename):
            size = os.path.getsize(filename) / 1024 / 1024
            write_log(f"Файл скачан: {filename}, размер: {size:.2f} MB")
            return filename

    write_log("[ERROR] Файл не найден после скачивания")
    return None

#Платформы 
def detect_platform(url: str) -> str:
    if "tiktok.com" in url:
        return "📹 TikTok"
    elif "youtube.com" in url or "youtu.be" in url:
        return "🎥 YouTube Shorts"
    elif "instagram.com" in url:
        return "📸 Instagram"
    else:
        return "🌍 Видео"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user = update.effective_user

    try:
        #Антиспам
        now = datetime.now()
        if user.id in last_request_time:
            if now - last_request_time[user.id] < timedelta(seconds=10):
                await update.message.reply_text("⏳ Подождите немного перед следующей загрузкой (лимит 1 видео / 10 секунд).")
                write_log(f"[WARN] Пользователь {user.id} слишком часто отправляет ссылки")
                return
        last_request_time[user.id] = now

        if not url.startswith(("http://", "https://")):
            await update.message.reply_text("❌ Пожалуйста, отправьте действительную ссылку.")
            write_log(f"[WARN] Пользователь {user.id} отправил невалидную ссылку: {url}")
            return

        await update.message.reply_text("⏳ Скачиваю видео, пожалуйста подождите...")
        write_log(f"Пользователь {user.id} ({user.username}) запросил: {url}")

        video_file = await run_yt_dlp(url)
        if not video_file:
            await update.message.reply_text("❌ Не удалось скачать видео. Проверьте ссылку.")
            write_log(f"[ERROR] Видео не скачано для {user.id}: {url}")
            return

        try:
            platform = detect_platform(url)
            update_stats(user.id, user.username)

            write_log(f"Отправляю видео пользователю {user.id}")
            with open(video_file, "rb") as f:
                await update.message.reply_video(
                    video=f,
                    caption=f"{platform}\nСпасибо нашему спонсору @VTSLYVPN_bot 🙏"
                )
            write_log(f"Видео отправлено пользователю {user.id}")
        finally:
            if os.path.exists(video_file):
                os.remove(video_file)
                write_log(f"Временный файл удалён: {video_file}")

    except (NetworkError, TimedOut):
        write_log(f"[ERROR] Сетевая ошибка при работе с пользователем {user.id}")
        await update.message.reply_text("⚠ Ошибка соединения с Telegram. Попробуйте ещё раз позже.")
    except Exception as e:
        write_log(f"[ERROR] Неизвестная ошибка: {e}")
        await update.message.reply_text("⚠ Произошла ошибка. Мы уже работаем над этим.")

#Админка
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📢 Рассылка (текст)", callback_data="broadcast_text")],
        [InlineKeyboardButton("📢 Рассылка (с кнопкой)", callback_data="broadcast_btn")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
    ]
    await update.message.reply_text("⚙ Админ-панель:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "broadcast_text":
        context.user_data["broadcast_mode"] = "text"
        await query.edit_message_text("✍ Введите текст для рассылки:")

    elif query.data == "broadcast_btn":
        context.user_data["broadcast_mode"] = "btn"
        await query.edit_message_text("✍ Введите сообщение в формате:\nТекст | Название кнопки | Ссылка")

    elif query.data == "stats":
        stats = {}
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    uid, count = line.strip().split(":", 1)
                    stats[uid] = int(count)
        text = f"👥 Пользователей: {len(load_users())}\n\n📊 Статистика скачиваний:\n"
        for k, v in stats.items():
            text += f"{k}: {v}\n"
        await query.edit_message_text(text)

async def admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    mode = context.user_data.get("broadcast_mode")
    if not mode:
        await handle_message(update, context)
        return

    text = update.message.text.strip()
    users = load_users()
    success, fail = 0, 0

    if mode == "text":
        for u in users:
            uid = int(u.split(" ")[0])
            try:
                await context.bot.send_message(uid, text)
                success += 1
            except Forbidden:
                remove_user(uid)
                fail += 1
            except Exception:
                fail += 1
        write_log(f"[ADMIN] Рассылка текста: \"{text}\" | Успешно: {success}, Ошибки: {fail}")
        await update.message.reply_text(f"✅ Рассылка завершена. Успешно: {success}, Ошибки: {fail}")

    elif mode == "btn":
        parts = text.split("|")
        if len(parts) != 3:
            await update.message.reply_text("❌ Формат: Текст | Название кнопки | Ссылка")
            return
        msg, btn_text, btn_url = map(str.strip, parts)
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=btn_url)]])
        for u in users:
            uid = int(u.split(" ")[0])
            try:
                await context.bot.send_message(uid, msg, reply_markup=markup)
                success += 1
            except Forbidden:
                remove_user(uid)
                fail += 1
            except Exception:
                fail += 1
        write_log(f"[ADMIN] Рассылка с кнопкой: \"{msg}\" ({btn_text} → {btn_url}) | Успешно: {success}, Ошибки: {fail}")
        await update.message.reply_text(f"✅ Рассылка завершена. Успешно: {success}, Ошибки: {fail}")

    context.user_data["broadcast_mode"] = None

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(admin_buttons))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), admin_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    write_log("Бот запущен и ожидает сообщения...")
    app.run_polling()

if __name__ == "__main__":
    main()
