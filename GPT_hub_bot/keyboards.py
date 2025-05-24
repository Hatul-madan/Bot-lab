from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_start_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🐾 Пойти в НИИИИИИ", url="https://t.me/NIIIIIIIIBot")]]
    )