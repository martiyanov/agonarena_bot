from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup


SELECT_SCENARIO_BUTTON = "🎯 Сценарии"
RANDOM_SCENARIO_BUTTON = "🎲 Случайный"
CUSTOM_SCENARIO_BUTTON = "🎭 Свой сценарий"
END_ROUND_BUTTON = "🏁 Завершить раунд"
RESULTS_BUTTON = "🏆 Итоги"
RULES_BUTTON = "ℹ️ Справка"
FEEDBACK_BUTTON = "💬 Отзыв"


def build_in_duel_keyboard(round_no: int, duel_id: int) -> InlineKeyboardMarkup:
    """Build inline keyboard with end round button for duel messages."""
    button_text = "🏁 Завершить раунд" if round_no == 1 else "🏁 Завершить поединок"
    callback_data = f"duel:v1:end:{duel_id}:{round_no}"
    
    keyboard = [
        [InlineKeyboardButton(text=button_text, callback_data=callback_data)]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_main_menu(has_active_duel: bool = False) -> ReplyKeyboardMarkup:
    """Build main menu keyboard with dynamic buttons based on duel state.
    
    Note: END_ROUND_BUTTON removed from reply keyboard - now using inline buttons.
    """
    # Keyboard is the same for both states now - END_ROUND moved to inline
    keyboard = [
        [
            KeyboardButton(text=SELECT_SCENARIO_BUTTON),
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
