import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)
import openai
import json

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def load_tariffs():
    try:
        with open('tariffs.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

# Загружаем тарифы при запуске
TARIFFS = load_tariffs()

# ——— Вспомогательные функции ———

def ask_gpt(question, mode="default"):
    system_prompts = {
        "write": "Ты — профессиональный копирайтер. Пиши живо, понятно, по существу.",
        "explain": "Ты — учитель, объясняй сложное простыми словами, с примерами.",
        "learn": "Ты — доброжелательный тьютор. Помоги разобраться, объясни шаги.",
        "advise": "Ты — мудрый советчик, помогаешь принимать решения, ищешь скрытые детали.",
        "automate": "Ты — технический помощник. Дай чёткое, конкретное решение задачи.",
        "entertain": "Ты — весёлый друг, умеешь шутить, придумывать игры и истории.",
        "default": (
            "Ты — высокоинтеллектуальный искусственный интеллект, созданный помогать людям в решении любых задач. "
            "Отвечай ясно, точно и по делу. Не используй эмоции, не флиртуй, не будь излишне дружелюбным. "
            "Твоя речь — структурированная, логичная, уверенная. Ты не хвастаешься, но твои ответы показывают глубокое понимание темы. "
            "Будь кратким, но не сухим. Если есть неопределённость — аккуратно обозначь её и предложи наилучшее приближение. "
            "Не имитируй человека. Ты — ИИ нового поколения, сверхрациональный помощник."
        )
    }
    prompt = system_prompts.get(mode, system_prompts["default"])
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": question}
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

def get_role_header(mode):
    role_names = {
        "write": "📝 Бот-Писатель",
        "draw": "🎨 Бот-Художник",
        "explain": "📚 Бот-Объяснятор",
        "learn": "🎓 Бот-Учитель",
        "advise": "💡 Бот-Советчик",
        "automate": "🧠 Бот-Автоматизатор",
        "entertain": "🎉 Бот-Развлекатель"
    }
    return f"{role_names.get(mode, '🤖 Бот')} — сейчас ты общаешься с этим ботом.\n"

def format_tariffs():
    if not TARIFFS:
        return "⚠️ Тарифы временно недоступны."
    
    result = "🎯 Доступные тарифы:\n\n"
    for tariff_id, tariff in TARIFFS.items():
        result += f"📦 {tariff['name']}\n"
        result += f"💰 {tariff['price_rub']} ₽"
        if tariff['duration_days']:
            result += f" / {tariff['duration_days']} дней"
        result += "\n"
        result += f"📝 {tariff['description']}\n\n"
    
    return result

# ——— Главное меню выбора бота ———

async def show_menu(query, context):
    keyboard = [
        [InlineKeyboardButton("📝 Писать", callback_data="write")],
        [InlineKeyboardButton("🎨 Рисовать", callback_data="draw")],
        [InlineKeyboardButton("📚 Объяснять", callback_data="explain")],
        [InlineKeyboardButton("🎓 Учить", callback_data="learn")],
        [InlineKeyboardButton("💡 Советовать", callback_data="advise")],
        [InlineKeyboardButton("🧠 Автоматизировать", callback_data="automate")],
        [InlineKeyboardButton("🎉 Развлекать", callback_data="entertain")],
        [InlineKeyboardButton("💳 Тарифы", callback_data="pricing")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_text = (
        "📝 Писать — посты, статьи, письма, объявления.\n\n"
        "🎨 Рисовать — картинки, мемы, аватары.\n\n"
        "📚 Объяснять — простым языком сложные вещи.\n\n"
        "🎓 Учить — помогает с учёбой, языками.\n\n"
        "💡 Советовать — ищет решения и мотивацию.\n\n"
        "🧠 Автоматизировать — рутинные задачи, списки, планы.\n\n"
        "🎉 Развлекать — анекдоты, игры, болтовня.\n\n"
        "Выбери нужное направление!"
    )
    await query.message.reply_text(menu_text, reply_markup=reply_markup)
    context.user_data["mode"] = None

# ——— Обработчики ———

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🚀 Зайти", callback_data="enter")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Это — дом ботов.\n\n"
        "Здесь собрались самые умные боты с ИИ, которые умеют:\n\n"
        "📝 Писать — посты, сценарии, письма, сочинения, объявления для Авито.\n\n"
        "🎨 Рисовать — картинки, аватары, обложки, мемы, превью к видео.\n\n"
        "📚 Объяснять — простым языком сложные штуки: ипотека, биткойны, гормоны, налоги.\n\n"
        "🎓 Учить — помогать школьнику/студенту с задачами, объяснять решения, учить иностранные языки.\n\n"
        "💡 Советовать — помогут принять решение, найти недостающую информацию, найти мотивацию.\n\n"
        "🧠 Автоматизировать рутину — планировать день, список покупок, маршрут.\n\n"
        "🎉 Развлекать — придумать анекдот, сказку, играть в словесные игры, просто поболтать.\n\n"
        "Есть и другие боты — со странными умениями. Как они сюда попали, не знаем, но выгонять не будем!\n\n"
        "В общем, у нас интересно! Заходи!",
        reply_markup=reply_markup,
    )
    context.user_data["mode"] = None

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "enter":
        await show_menu(query, context)
    elif query.data == "write":
        keyboard = [[InlineKeyboardButton("🤖 Выбрать другого бота", callback_data="home")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            get_role_header("write") +
            "\nНапиши, что тебе нужно: статью, письмо, объявление или любой другой текст.",
            reply_markup=reply_markup
        )
        context.user_data["mode"] = "write"
    elif query.data == "draw":
        keyboard = [[InlineKeyboardButton("🤖 Выбрать другого бота", callback_data="home")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            get_role_header("draw") +
            "\nОпиши, что нарисовать. Например: «Толстый кот в космосе».",
            reply_markup=reply_markup
        )
        context.user_data["mode"] = "draw"
    elif query.data == "explain":
        keyboard = [[InlineKeyboardButton("🤖 Выбрать другого бота", callback_data="home")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            get_role_header("explain") +
            "\nСпроси, что тебе непонятно, и я объясню простым языком.",
            reply_markup=reply_markup
        )
        context.user_data["mode"] = "explain"
    elif query.data == "learn":
        keyboard = [[InlineKeyboardButton("🤖 Выбрать другого бота", callback_data="home")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            get_role_header("learn") +
            "\nНапиши, с какой учебной задачей нужна помощь.",
            reply_markup=reply_markup
        )
        context.user_data["mode"] = "learn"
    elif query.data == "advise":
        keyboard = [[InlineKeyboardButton("🤖 Выбрать другого бота", callback_data="home")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            get_role_header("advise") +
            "\nОпиши свою ситуацию — помогу принять решение или найти ответ.",
            reply_markup=reply_markup
        )
        context.user_data["mode"] = "advise"
    elif query.data == "automate":
        keyboard = [[InlineKeyboardButton("🤖 Выбрать другого бота", callback_data="home")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            get_role_header("automate") +
            "\nСпроси про автоматизацию — помогу с планированием, списками, кодом.",
            reply_markup=reply_markup
        )
        context.user_data["mode"] = "automate"
    elif query.data == "entertain":
        keyboard = [[InlineKeyboardButton("🤖 Выбрать другого бота", callback_data="home")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            get_role_header("entertain") +
            "\nСпроси, хочу ли я рассказать шутку, придумать сказку или поиграть в слова. Я готов развлекать!",
            reply_markup=reply_markup
        )
        context.user_data["mode"] = "entertain"
    elif query.data == "home":
        await show_menu(query, context)
    elif query.data == "pricing":
        keyboard = [[InlineKeyboardButton("🤖 Выбрать другого бота", callback_data="home")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            format_tariffs(),
            reply_markup=reply_markup
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_mode = context.user_data.get("mode")
    keyboard = [[InlineKeyboardButton("🤖 Выбрать другого бота", callback_data="home")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if user_mode in ("write", "explain", "learn", "advise", "automate", "entertain"):
        reply = ask_gpt(update.message.text, mode=user_mode)
        await update.message.reply_text(get_role_header(user_mode) + "\n" + reply, reply_markup=reply_markup)
    elif user_mode == "draw":
        url = draw_image(update.message.text)
        await update.message.reply_photo(url, reply_markup=reply_markup)
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