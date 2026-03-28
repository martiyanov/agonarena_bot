from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


SELECT_SCENARIO_BUTTON = "🎯 Выбрать сценарий"
RANDOM_SCENARIO_BUTTON = "🎲 Случайный сценарий"
CUSTOM_SCENARIO_BUTTON = "🎭 Свой сценарий"
END_ROUND_BUTTON = "🏁 Завершить раунд"
RESULTS_BUTTON = "🏆 Итоги"
RULES_BUTTON = "ℹ️ Справка"
FEEDBACK_BUTTON = "💬 Обратная связь"


def build_main_menu(has_active_duel: bool = False) -> ReplyKeyboardMarkup:
    """Build main menu keyboard with dynamic buttons based on duel state."""
    keyboard = [
        [
            KeyboardButton(text=SELECT_SCENARIO_BUTTON),
            KeyboardButton(text=RANDOM_SCENARIO_BUTTON),
            KeyboardButton(text=CUSTOM_SCENARIO_BUTTON),
        ],
    ]
    
    if has_active_duel:
        # Show duel-related buttons only when duel is active
        keyboard.append([
            KeyboardButton(text=END_ROUND_BUTTON),
            KeyboardButton(text=RESULTS_BUTTON),
        ])
    
    keyboard.append([
        KeyboardButton(text=RULES_BUTTON),
        KeyboardButton(text=FEEDBACK_BUTTON),
    ])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )
