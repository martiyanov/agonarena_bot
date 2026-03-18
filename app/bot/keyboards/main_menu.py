from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def build_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="⚔️ Поединок"),
            ],
            [
                KeyboardButton(text="⏭️ Раунд 2"),
                KeyboardButton(text="🏁 Завершить"),
            ],
            [
                KeyboardButton(text="ℹ️ Справка"),
            ],
        ],
        resize_keyboard=True,
    )
