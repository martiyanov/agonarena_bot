from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


SELECT_SCENARIO_BUTTON = "🎯 Выбрать сценарий"
RANDOM_SCENARIO_BUTTON = "🎲 Случайный сценарий"
CUSTOM_SCENARIO_BUTTON = "🎭 Свой сценарий"
END_ROUND_BUTTON = "🏁 Завершить раунд"
RULES_BUTTON = "ℹ️ Справка"
FEEDBACK_BUTTON = "💬 Обратная связь"


def build_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=SELECT_SCENARIO_BUTTON),
                KeyboardButton(text=RANDOM_SCENARIO_BUTTON),
                KeyboardButton(text=CUSTOM_SCENARIO_BUTTON),
            ],
            [
                KeyboardButton(text=END_ROUND_BUTTON),
            ],
            [
                KeyboardButton(text=RULES_BUTTON),
                KeyboardButton(text=FEEDBACK_BUTTON),
            ],
        ],
        resize_keyboard=True,
    )
