import os
import openai
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)
from users import init_db, add_user, get_stats
from petrovich.main import Petrovich

# --- Petrovich instance
p = Petrovich()

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Память и режимы
user_memory = {}
user_modes = {}

# Загрузка персонажей из файла
with open("characters.json", "r", encoding="utf-8") as f:
    modes = json.load(f)

def guess_gender(name):
    """Определяет пол по имени, используя Petrovich."""
    if not name or len(name) < 2:
        return "unknown"
    gender = p.firstname.gender(name)
    if gender not in ("male", "female"):
        return "unknown"
    return gender

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    first_name = update.effective_user.first_name or ""
    add_user(user_id, username)

    gender = guess_gender(first_name)
    # Дуракоустойчивость: имя должно быть не короче 2 символов, пол определён
    if not first_name or len(first_name) < 2 or gender == "unknown":
        first_name = ""
        gender = "unknown"
    user_memory[user_id] = {
        "history": [],
        "name": first_name,
        "gender": gender,
        "asked_name": False
    }
    await update.message.reply_text("Че надо?")

# /reset
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name or ""
    gender = guess_gender(first_name)
    if not first_name or len(first_name) < 2 or gender == "unknown":
        first_name = ""
        gender = "unknown"
    user_memory[user_id] = {
        "history": [],
        "name": first_name,
        "gender": gender,
        "asked_name": False
    }
    await update.message.reply_text("🔄 Память очищена!\nЧе надо?")

# /mode
async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("❗ Укажи режим: /mode хам | секретарь | няша")
        return

    mode = args[0].lower()
    if mode not in modes:
        await update.message.reply_text("❗ Неизвестный режим.")
        return

    user_modes[user_id] = mode
    await update.message.reply_text(f"✅ Режим установлен: {mode}")

# /stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total, today, week = get_stats()
    await update.message.reply_text(
        f"👥 Всего пользователей: {total}\n"
        f"📅 Сегодня: {today}\n"
        f"📆 За 7 дней: {week}"
    )

# /reload_modes
async def reload_modes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global modes
    try:
        with open("characters.json", "r", encoding="utf-8") as f:
            modes = json.load(f)
        await update.message.reply_text(f"🔁 Персонажи перезагружены. Загружено стилей: {len(modes)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при загрузке: {e}")

# --- Имя юзера (только если не определили сразу)
async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_input = update.message.text.strip()
    gender = guess_gender(user_input)
    if gender == "unknown":
        user_memory[user_id]["name"] = ""
        user_memory[user_id]["gender"] = "unknown"
        user_memory[user_id]["asked_name"] = True
        await update.message.reply_text("Имя что-то странное. Назови себя нормально!")
        return
    user_memory[user_id]["name"] = user_input
    user_memory[user_id]["gender"] = gender
    user_memory[user_id]["asked_name"] = True
    await update.message.reply_text("Принято. Че надо?")

# Основной обработчик сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_input = update.message.text.strip()

    memory = user_memory.get(user_id)

    # 1. Если ещё не определён пол, и имя из профиля отсутствует или не сработало — уточняем имя (но не сразу!)
    if memory:
        if memory.get("gender", "unknown") == "unknown" and not memory.get("asked_name"):
            user_memory[user_id]["asked_name"] = True
            await update.message.reply_text("Кстати, я Валера. А тебя как звать?")
            return
        elif memory.get("gender", "unknown") == "unknown" and memory.get("asked_name"):
            await handle_name(update, context)
            return

    # --- Дальше стандартный диалог, имя НЕ вставляем, только используем пол для правильной грамматики
    mode = user_modes.get(user_id, "default")
    system_prompt = modes.get(mode, modes["default"])

    history = memory.get("history", []) if memory else []
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-15:])
    messages.append({"role": "user", "content": user_input})

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )

    reply = response.choices[0].message.content.strip()

    if memory is not None:
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})
        user_memory[user_id]["history"] = history

    await update.message.reply_text(reply)

# --- Запуск
def main():
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("mode", set_mode))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("reload_modes", reload_modes))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
