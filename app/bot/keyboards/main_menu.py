from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def build_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚔️ Начать поединок")],
            [KeyboardButton(text="✍️ Сделать ход"), KeyboardButton(text="⏭️ Следующий раунд")],
            [KeyboardButton(text="🏁 Завершить поединок"), KeyboardButton(text="🏆 Мои результаты")],
            [KeyboardButton(text="📚 Сценарии"), KeyboardButton(text="ℹ️ Как это работает")],
        ],
        resize_keyboard=True,
    )
