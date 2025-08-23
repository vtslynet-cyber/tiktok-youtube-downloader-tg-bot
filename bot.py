import sys, os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import re
import glob
import asyncio
import contextlib
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)
from telegram.error import NetworkError, TimedOut, Forbidden

#Token + admin id
TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER" 
ADMIN_ID = ВАШ_ID_ЧИСЛОМ
#На Windows укажем путь, на Linux оставим пусто (будет взят из PATH)
FFMPEG_DIR = os.environ.get("FFMPEG_DIR", r"D:\primer\ffmpeg\bin" if os.name == "nt" else "")
#файлы пользователей, логов, статистики, cookies
USERS_FILE = os.path.join(BASE_DIR, "users.txt")
LOG_FILE   = os.path.join(BASE_DIR, "bot.log")
STATS_FILE = os.path.join(BASE_DIR, "stats.txt")
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.txt")
from downloaders.pinterest_async import download_pinterest_video

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
                if ":" in line:
                    uid, count = line.strip().split(":", 1)
                    try:
                        stats[uid] = int(count)
                    except:
                        stats[uid] = 0
    key = f"{user_id} ({username})"
    stats[key] = stats.get(key, 0) + 1
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        for k, v in stats.items():
            f.write(f"{k}:{v}\n")
#yt-dlp
async def run_yt_dlp(url: str) -> str | None:
    """
    Качаем в стримабельный MP4 (H.264+AAC).
    Запуск через sys.executable -m yt_dlp (не зависит от PATH в systemd).
    Плюс защита, если процесс не стартовал.
    """
    ytdlp_fmt = (
        "bv*[ext=mp4][vcodec^=avc1][height<=1080]+ba[ext=m4a]/"
        "b[ext=mp4]/best"
    )
    out_tmpl = "yt_%(id)s.%(ext)s"
    #t-dlp(v2)
    args = [
        sys.executable, "-m", "yt_dlp", url,
        "-f", ytdlp_fmt,
        "--merge-output-format", "mp4",
        "--remux-video", "mp4",
        "--postprocessor-args", "ffmpeg:-movflags +faststart",
        "--no-playlist",
        "--no-continue",
        "--retries", "3",
        "--http-chunk-size", "5M",
        "--restrict-filenames",
        "-o", out_tmpl,
    ]

    #cookies
    if os.path.exists(COOKIES_FILE):
        args += ["--cookies", COOKIES_FILE]
    else:
        write_log("[INFO] cookies.txt не найден — продолжаю без него")

    #ffmpeg-location только если путь валиден (актуально для Windows)
    if FFMPEG_DIR and os.path.isdir(FFMPEG_DIR):
        args += ["--ffmpeg-location", FFMPEG_DIR]
    else:
        write_log("[INFO] ffmpeg-location не задан — использую системный ffmpeg из PATH")

    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
    except asyncio.TimeoutError:
        if proc:
            with contextlib.suppress(Exception):
                proc.kill()
        write_log("[ERROR] yt-dlp timeout (превышено время ожидания)")
        return None
    except FileNotFoundError as e:
        write_log(f"[ERROR] Не найден yt-dlp/python для запуска: {e}")
        return None
    except Exception as e:
        # если процесс запущен — аккуратно завершим
        if proc and proc.returncode is None:
            with contextlib.suppress(Exception):
                proc.kill()
        write_log(f"[ERROR] Ошибка запуска yt-dlp: {e}")
        return None

    out = stdout.decode("utf-8", errors="ignore")
    err = stderr.decode("utf-8", errors="ignore")

    write_log(f"yt-dlp stdout:\n{out}")
    if err.strip():
        write_log(f"yt-dlp stderr:\n{err}")

    # ищем итоговый mp4
    patterns = [
        r'\[Merger\] Merging formats into "(.+?\.mp4)"',
        r'\[download\] Destination: (.+?\.mp4)',
        r'\[AtomicParsley\] Writing metadata to file: (.+?\.mp4)',
    ]
    filename = None
    for pat in patterns:
        m = re.search(pat, out)
        if m:
            filename = m.group(1).strip()
            break

    if not filename:
        mp4s = sorted(glob.glob("yt_*.mp4"), key=os.path.getmtime, reverse=True)
        if mp4s:
            filename = mp4s[0]

    if not filename or not os.path.exists(filename):
        write_log("[ERROR] Файл не найден после скачивания")
        return None

    size = os.path.getsize(filename) / 1024 / 1024
    write_log(f"Файл скачан: {filename}, размер: {size:.2f} MB")
    return filename

def detect_platform(url: str) -> str:
    u = url.lower()
    if "tiktok.com" in u:
        return "📹 TikTok"
    elif "youtube.com" in u or "youtu.be" in u:
        return "🎥 YouTube"
    elif "instagram.com" in u:
        return "📸 Instagram"
    elif "pinterest.com" in u or "pin.it" in u:
        return "📌 Pinterest"
    else:
        return "🌍 Видео"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.username)
    write_log(f"Пользователь {user.id} ({user.username}) нажал /start")

    keyboard = [[InlineKeyboardButton("🔥 Поддержать проект и купить ключ", url="https://t.me/VTSLYVPN_bot")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Привет! Отправь мне ссылку на видео (TikTok, YouTube, Instagram, Pinterest), "
        "и я скачаю его без водяных знаков.",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user = update.effective_user

    try:
        #Антиспам
        now = datetime.now()
        if user.id in last_request_time and (now - last_request_time[user.id] < timedelta(seconds=10)):
            await update.message.reply_text("⏳ Подождите немного перед следующей загрузкой (лимит 1 видео / 10 секунд).")
            write_log(f"[WARN] Пользователь {user.id} слишком часто отправляет ссылки")
            return
        last_request_time[user.id] = now

        if not url.startswith(("http://", "https://")):
            await update.message.reply_text(
                "❌ Пожалуйста, отправьте действительную ссылку.\n\n"
                "📌 Поддерживаемые платформы:\n"
                "• TikTok (tiktok.com)\n"
                "• YouTube (youtube.com, youtu.be)\n"
                "• Instagram (instagram.com)\n"
                "• Pinterest (pinterest.com, pin.it)"
            )
            write_log(f"[WARN] Пользователь {user.id} отправил невалидную ссылку: {url}")
            return

        await update.message.reply_text("⏳ Скачиваю видео, пожалуйста подождите...")
        write_log(f"Пользователь {user.id} ({user.username}) запросил: {url}")

        platform = detect_platform(url)

        #Pinterest
        if "pinterest.com" in url.lower() or "pin.it" in url.lower():
            try:
                path = await download_pinterest_video(url)
                video_file = str(path)
            except Exception as e:
                write_log(f"[ERROR] Pinterest загрузка: {e}")
                await update.message.reply_text("❌ Не удалось скачать видео из Pinterest. Проверьте, что это видео-пин.")
                return
        else:
            video_file = await run_yt_dlp(url)
            if not video_file:
                await update.message.reply_text("❌ Не удалось скачать видео. Проверьте ссылку.")
                write_log(f"[ERROR] Видео не скачано для {user.id}: {url}")
                return

        try:
            update_stats(user.id, user.username)
            write_log(f"Отправляю видео пользователю {user.id}")
            with open(video_file, "rb") as f:
                await update.message.reply_video(
                    video=f,
                    supports_streaming=True,
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
                    if ":" in line:
                        uid, count = line.strip().split(":", 1)
                        try:
                            stats[uid] = int(count)
                        except:
                            stats[uid] = 0
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
