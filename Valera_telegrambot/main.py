import os
import openai
import json
import re
import random
from typing import Dict, List, TypedDict, Literal
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


# --- INIT ---
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY


# --- Загрузка словаря имён ---
def load_name_gender_map() -> Dict[str, str]:
    try:
        with open("name_gender_map.json", "r", encoding="utf-8") as f:
            raw_map = json.load(f)
            name_map = {}
            
            # Обработка мужских имён
            male_names = raw_map.get(
                "// МУЖСКИЕ ИМЕНА", {}
            )
            for full_name, variations in male_names.items():
                for name, gender in variations.items():
                    name_map[name.lower()] = gender
            
            # Обработка женских имён
            female_names = raw_map.get(
                "// ЖЕНСКИЕ ИМЕНА", {}
            )
            for full_name, variations in female_names.items():
                for name, gender in variations.items():
                    name_map[name.lower()] = gender
            
            # Обработка неопределённых имён
            unknown_names = raw_map.get(
                "// ИМЕНА, КОТОРЫЕ МОГУТ БЫТЬ И МУЖСКИМИ И ЖЕНСКИМИ", 
                {}
            )
            for full_name, variations in unknown_names.items():
                for name, gender in variations.items():
                    name_map[name.lower()] = gender
            
            return name_map
    except Exception as e:
        print(
            f"Ошибка загрузки name_gender_map.json: {e}. "
            "Использую базовый словарь."
        )
        return {
            "сергей": "male", "евгений": "male", "александр": "male",
            "анна": "female", "мария": "female", "елена": "female"
        }


# --- Загрузка промптов ---
def load_characters():
    try:
        with open("characters.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        print("Ошибка загрузки characters.json. Использую базовый промпт.")
        return {
            "valera": {
                "prompt": (
                    "Тебя зовут Валера. Ты грубый, раздражённый, "
                    "и язвительный ИИ. Отвечай коротко и резко."
                ),
                "model": "gpt-4o",
                "temperature": 0.9
            }
        }


# Загружаем данные при старте
name_gender_map = load_name_gender_map()
characters = load_characters()


# --- Глобальные переменные ---
user_memory: Dict[int, List[ChatMessage]] = {}
user_gender: Dict[int, str] = {}
user_state: Dict[int, str] = {}
# Счетчик сообщений для каждого пользователя
message_counter: Dict[int, int] = {}


def load_promo_messages() -> List[str]:
    """Загружает промо-сообщения из файла"""
    try:
        with open("promo_messages.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("messages", [])
    except Exception as e:
        print(f"Ошибка загрузки promo_messages.json: {e}")
        return []


# Загружаем промо-сообщения при старте
promo_messages = load_promo_messages()


def guess_gender_by_name(name: str) -> str:
    """Определяет пол по имени из словаря"""
    if not name:
        return "unknown"
    
    # Берём только первое слово (имя без фамилии)
    first_word = name.strip().split()[0] if name.strip() else ""
    clean_name = first_word.lower()
    
    return name_gender_map.get(clean_name, "unknown")


def extract_name_from_text(text: str) -> str:
    """Извлекает имя из текста пользователя"""
    text = text.strip()
    
    # Паттерны для поиска имени
    patterns = [
        r'меня зовут\s+([А-ЯЁ][а-яё]+)',
        r'я\s+([А-ЯЁ][а-яё]+)',
        r'зовут\s+([А-ЯЁ][а-яё]+)',
        r'\b([А-ЯЁ][а-яё]+)\b'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1)
            # Исключаем служебные слова
            excluded = ['меня', 'зовут', 'тебя', 'как', 'что', 'где', 'когда']
            if name.lower() not in excluded:
                return name
    
    return ""


def detect_gender_from_response(text: str) -> str:
    """Определяет пол из прямого ответа"""
    text_lower = text.lower()
    
    male_words = ['мальчик', 'парень', 'мужчина', 'я мальчик', 'я парень']
    female_words = ['девочка', 'женщина', 'девушка', 'я девочка', 'я девушка']
    
    for word in male_words:
        if word in text_lower:
            return "male"
    
    for word in female_words:
        if word in text_lower:
            return "female"
    
    return "unknown"


def build_system_prompt(gender: str) -> str:
    """Создаёт системный промпт с учётом пола"""
    if gender == "male":
        gender_info = "Пол собеседника: мужской."
    elif gender == "female":
        gender_info = "Пол собеседника: женский."
    else:
        gender_info = "Пол собеседника: неизвестно."
    
    # Берём промпт "valera" из characters.json
    char_config = characters.get("valera", {
        "prompt": [
            "Ты Валера, грубый помощник."
        ]
    })
    
    # Объединяем строки промпта
    base_prompt = " ".join(char_config["prompt"])
    
    return f"{base_prompt}\n{gender_info}"


# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name or ""
    
    # Пытаемся определить пол по имени из профиля
    gender = guess_gender_by_name(first_name)
    user_gender[user_id] = gender
    user_memory[user_id] = []
    message_counter[user_id] = 0
    
    if gender in ["male", "female"]:
        user_state[user_id] = "determined"
    else:
        user_state[user_id] = "initial"
    
    await update.message.reply_text("Че надо?")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name or ""
    
    # Очищаем память и счетчик
    user_memory[user_id] = []
    message_counter[user_id] = 0
    
    # Заново определяем пол по имени из профиля
    gender = guess_gender_by_name(first_name)
    user_gender[user_id] = gender
    
    # Устанавливаем правильное состояние
    if gender in ["male", "female"]:
        user_state[user_id] = "determined"
    else:
        user_state[user_id] = "initial"
    
    await update.message.reply_text("🔄 Память очищена!\nЧе надо?")


# --- Основной обработчик ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    text = update.message.text
    if not text:
        return
    text = text.strip()
    
    # Инициализация если пользователь новый
    if user_id not in user_state:
        user_state[user_id] = "initial"
        user_gender[user_id] = "unknown"
        user_memory[user_id] = []
    
    state = user_state[user_id]
    gender = user_gender[user_id]
    
    # Логика по состояниям
    if state == "initial":
        # Первое сообщение
        user_memory[user_id].append({"role": "user", "content": text})
        response_text = await generate_response(user_id, text)
        await update.message.reply_text(response_text)
        user_state[user_id] = "waiting_name"
        
    elif state == "waiting_name":
        # Второе сообщение - спрашиваем имя
        user_memory[user_id].append({"role": "user", "content": text})
        response_text = await generate_response(user_id, text)
        
        # Добавляем вопрос об имени
        full_response = (
            f"{response_text}\n\n"
            "Кстати, я Валера. А тебя как звать?"
        )
        await update.message.reply_text(full_response)
        user_state[user_id] = "analyzing_name"
        
    elif state == "analyzing_name":
        # Анализируем ответ на вопрос об имени
        user_memory[user_id].append({"role": "user", "content": text})
        
        extracted_name = extract_name_from_text(text)
        if extracted_name:
            gender = guess_gender_by_name(extracted_name)
            user_gender[user_id] = gender
            
            if gender in ["male", "female"]:
                user_state[user_id] = "determined"
                await update.message.reply_text("Ок, понял.")
                return
            else:
                user_state[user_id] = "waiting_gender"
                await update.message.reply_text(
                    "Не понял. Это ты мальчик, или девочка?"
                )
                return
        else:
            user_state[user_id] = "waiting_gender"
            await update.message.reply_text(
                "Не понял. Это ты мальчик, или девочка?"
            )
            return
            
    elif state == "waiting_gender":
        # Анализируем прямой ответ о поле
        detected_gender = detect_gender_from_response(text)
        
        if detected_gender in ["male", "female"]:
            user_gender[user_id] = detected_gender
            user_state[user_id] = "determined"
            await update.message.reply_text("Ок, понял.")
            return
        else:
            user_gender[user_id] = "unknown"
            user_state[user_id] = "determined"
            await update.message.reply_text("Ладно, фиг с тобой.")
            return
    
    elif state == "determined":
        # Обычное общение
        user_memory[user_id].append({"role": "user", "content": text})
        response_text = await generate_response(user_id, text)
        await update.message.reply_text(response_text)


async def generate_response(user_id: int, text: str) -> str:
    """Генерирует ответ с учётом пола пользователя"""
    gender = user_gender.get(user_id, "unknown")
    
    # Обновляем счетчик сообщений
    message_counter[user_id] = message_counter.get(user_id, 0) + 1
    
    # Получаем конфигурацию персонажа
    char_config = characters.get("valera", {
        "model": "gpt-4o",
        "temperature": 0.9
    })
    
    # Формируем системный промпт
    system_prompt = build_system_prompt(gender)
    
    # История сообщений
    history = user_memory.get(user_id, [])
    messages = [
        {"role": "system", "content": system_prompt},
        *history[-15:],
        {"role": "user", "content": text}
    ]
    
    # Запрос к OpenAI
    try:
        response = openai.chat.completions.create(
            model=char_config["model"],
            messages=messages,
            temperature=char_config["temperature"]
        )
        if not response.choices[0].message.content:
            return "Чет у меня глюк. Попробуй еще раз."
        
        reply = response.choices[0].message.content.strip()
        
        # Добавляем в память
        user_memory[user_id].append({"role": "assistant", "content": reply})
        
        # Проверяем, нужно ли добавить промо-сообщение
        if (message_counter[user_id] % random.randint(10, 15) == 0 and 
                promo_messages):
            promo = random.choice(promo_messages)
            reply = f"{reply}\n\n{promo}"
        
        return reply
    except Exception:
        return "Чет у меня глюк. Попробуй еще раз."


# --- Запуск ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                  handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()