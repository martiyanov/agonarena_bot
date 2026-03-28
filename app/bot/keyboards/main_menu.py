from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


SELECT_SCENARIO_BUTTON = "🎯 Сценарии"
RANDOM_SCENARIO_BUTTON = "🎲 Случайный"
CUSTOM_SCENARIO_BUTTON = "🎭 Свой сценарий"
END_ROUND_BUTTON = "🏁 Завершить раунд"
RESULTS_BUTTON = "🏆 Итоги"
RULES_BUTTON = "ℹ️ Справка"
FEEDBACK_BUTTON = "💬 Отзыв"


def build_main_menu(has_active_duel: bool = False) -> ReplyKeyboardMarkup:
    """Build main menu keyboard with dynamic buttons based on duel state."""
    if has_active_duel:
        # Keyboard in_duel: 5 buttons
        keyboard = [
            [
                KeyboardButton(text=END_ROUND_BUTTON),
            ],
            [
                KeyboardButton(text=SELECT_SCENARIO_BUTTON),
                KeyboardButton(text=RANDOM_SCENARIO_BUTTON),
            ],
            [
                KeyboardButton(text=RULES_BUTTON),
                KeyboardButton(text=FEEDBACK_BUTTON),
            ],
        ]
    else:
        # Keyboard idle: 4 buttons
        keyboard = [
            [
                KeyboardButton(text=SELECT_SCENARIO_BUTTON),
                KeyboardButton(text=RANDOM_SCENARIO_BUTTON),
            ],
            [
                KeyboardButton(text=RULES_BUTTON),
                KeyboardButton(text=FEEDBACK_BUTTON),
            ],
        ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )
