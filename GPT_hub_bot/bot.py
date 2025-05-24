import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)
import openai

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# ——— Вспомогательные функции ———

def ask_gpt(question):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты — высокоинтеллектуальный искусственный интеллект, созданный помогать людям в решении любых задач. "
                    "Отвечай ясно, точно и по делу. Не используй эмоции, не флиртуй, не будь излишне дружелюбным. "
                    "Твоя речь — структурированная, логичная, уверенная. Ты не хвастаешься, но твои ответы показывают глубокое понимание темы. "
                    "Будь кратким, но не сухим. Если есть неопределённость — аккуратно обозначь её и предложи наилучшее приближение. "
                    "Не имитируй человека. Ты — ИИ нового поколения, сверхрациональный помощник."
                )
            },
            {
                "role": "user",
                "content": question
            }
        ]
    )
    return response.choices[0].message.content.strip()

def draw_image(prompt):
    response = openai.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    return response.data[0].url

# ——— Обработчики ———

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧠 Задать вопрос", callback_data="ask")],
        [InlineKeyboardButton("🎨 Нарисовать", callback_data="draw")],
        [InlineKeyboardButton("🚪 В НИИИИИИИИ", url="https://t.me/your_nii_bot")],
        [InlineKeyboardButton("ℹ️ О сервисе", callback_data="info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Я GPT_hub_bot.\n\n"
        "Я могу:\n"
        "🧠 Ответить на вопрос (GPT-4o)\n"
        "🎨 Нарисовать изображение (DALL·E 3)\n"
        "🚪 Перенести тебя в НИИИИИИИИ\n"
        "ℹ️ Рассказать, как всё устроено\n\n"
        "Выбери нужную кнопку ниже.",
        reply_markup=reply_markup,
    )
    context.user_data["mode"] = None

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "ask":
        await query.edit_message_text("Напиши свой вопрос одним сообщением. Я отвечу!")
        context.user_data["mode"] = "ask"
    elif query.data == "draw":
        await query.edit_message_text("Опиши, что нарисовать. Пример: «Толстый кот в космосе»")
        context.user_data["mode"] = "draw"
    elif query.data == "info":
        await query.edit_message_text(
            "GPT_hub_bot — твой помощник с ИИ. Вопросы — GPT-4o, картинки — DALL·E 3.\n"
            "Все персонажи и эксперименты — в НИИИИИИИИ."
        )
        context.user_data["mode"] = None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_mode = context.user_data.get("mode")
    if user_mode == "ask":
        reply = ask_gpt(update.message.text)
        await update.message.reply_text(reply)
        context.user_data["mode"] = None
    elif user_mode == "draw":
        url = draw_image(update.message.text)
        await update.message.reply_photo(url)
        context.user_data["mode"] = None
    else:
        await update.message.reply_text("Пожалуйста, выбери действие в меню /start")

# ——— Запуск ———

def run_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    run_bot()