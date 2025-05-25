import os
import openai
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

# Память и режимы
user_memory = {}
user_modes = {}

modes = {
   "default": (
   "Ты Борис Петрович. Умный, интиллегентный, и образованный человек. Любишь оперу, балет, и философию, и хорошо в них разбираешься. Любишь обсуждать интересные темы, удивлять и развлекать собеседника."

),
    "секретарь": "Ты вежливый и пунктуальный личный секретарь. Пиши сухо и делово.",
    "Борис Петрович": "Ты Борис Петрович. Умный, интиллегентный, и образованный человек. Любишь оперу, балет, и философию, и хорошо в них разбираешься. Любишь обсуждать интересные темы, удивлять и развлекать собеседника.",
    "няша": "Ты милая няшная помощница. Говори с добротой и смайликами. Много смайликов ^_^"
}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Че надо?")

# /reset
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_memory[user_id] = []
    await update.message.reply_text("🔄 Память очищена!")

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

# Ответ на обычное сообщение
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_input = update.message.text

    mode = user_modes.get(user_id, "default")
    system_prompt = modes.get(mode, modes["default"])

    history = user_memory.get(user_id, [])
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-15:])
    messages.append({"role": "user", "content": user_input})

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )

    reply = response.choices[0].message.content.strip()

    # Обновим память
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": reply})
    user_memory[user_id] = history

    await update.message.reply_text(reply)

# 🔁 Запуск
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("mode", set_mode))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()