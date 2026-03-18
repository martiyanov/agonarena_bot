from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def build_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚔️ Начать поединок")],
            [KeyboardButton(text="✍️ Отправить реплику"), KeyboardButton(text="⏭️ Следующий раунд")],
            [KeyboardButton(text="🏁 Завершить поединок"), KeyboardButton(text="🏆 Результаты")],
            [KeyboardButton(text="📚 Сценарии"), KeyboardButton(text="ℹ️ Правила")],
        ],
        resize_keyboard=True,
    )
