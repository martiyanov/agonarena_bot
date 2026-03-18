from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


MAIN_MENU_ROWS = [
    [
        KeyboardButton(text="⚔️ Поединок"),
        KeyboardButton(text="✍️ Ход"),
        KeyboardButton(text="⏭️ Раунд 2"),
    ],
    [
        KeyboardButton(text="🏁 Завершить"),
        KeyboardButton(text="📚 Сценарии"),
        KeyboardButton(text="⋯ Ещё"),
    ],
]


MORE_MENU_ROWS = [
    [
        KeyboardButton(text="🏆 Итоги"),
        KeyboardButton(text="ℹ️ Правила"),
    ],
    [KeyboardButton(text="⬅️ Назад")],
]


def build_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=MAIN_MENU_ROWS, resize_keyboard=True)


def build_more_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=MORE_MENU_ROWS, resize_keyboard=True)
