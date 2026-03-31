"""
Staging Test: Кнопка "🎯 Сценарии" на staging окружении

Запускается локально без Telegram webhook.
Проверяет что код на staging использует правильный обработчик.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Staging env
os.environ["APP_ENV"] = "staging"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/staging_test.db"


def test_staging_code_has_fix():
    """Проверяет что код в staging использует правильный обработчик."""
    import inspect
    from app.bot.handlers.menu import handle_start_button, START_BUTTON, _send_scenario_picker
    
    # Проверяем исходный код функции
    source = inspect.getsource(handle_start_button)
    
    # Фикс должен вызывать _send_scenario_picker
    assert "_send_scenario_picker" in source, \
        "handle_start_button должен вызывать _send_scenario_picker"
    
    # Не должен вызывать show_main_menu
    assert "show_main_menu" not in source, \
        "handle_start_button НЕ должен вызывать show_main_menu"
    
    print("✅ Staging code has the fix!")


def test_start_button_constant():
    """Проверяет что константа START_BUTTON правильная."""
    from app.bot.handlers.menu import START_BUTTON
    from app.bot.keyboards.main_menu import SELECT_SCENARIO_BUTTON
    
    # Кнопка в клавиатуре и обработчик должны использовать одно значение
    assert START_BUTTON == "🎯 Сценарии", \
        f"START_BUTTON должен быть '🎯 Сценарии', а не '{START_BUTTON}'"
    
    assert SELECT_SCENARIO_BUTTON == "🎯 Сценарии", \
        f"SELECT_SCENARIO_BUTTON должен быть '🎯 Сценарии', а не '{SELECT_SCENARIO_BUTTON}'"
    
    print("✅ Button constants match!")


if __name__ == "__main__":
    test_staging_code_has_fix()
    test_start_button_constant()
    print("\n✅ All staging tests passed!")
