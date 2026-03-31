"""
Test: Кнопка "🎯 Сценарии" показывает список сценариев даже при активном поединке

Bug: Кнопка "🎯 Сценарии" показывала "Поединок уже идёт..." вместо списка сценариев
Fix: Кнопка должна всегда показывать список сценариев
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB_PATH = ROOT / "data" / "agonarena_test_scenario_button.db"
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

import app.config as app_config
from app.db import session as db_session
from app.db.init_db import init_db
from app.db.models import Scenario, Duel, DuelRound
from app.services.duel_service import DuelService

app_config.settings = app_config.Settings()


@pytest.fixture(autouse=True)
async def fresh_test_db():
    """Инициализация чистой тестовой БД перед каждым тестом."""
    TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if db_session.engine is not None:
        await db_session.engine.dispose()

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    db_session.configure_database(f"sqlite+aiosqlite:///{TEST_DB_PATH}")
    await init_db()

    yield

    if db_session.engine is not None:
        await db_session.engine.dispose()

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


def _create_mock_message(text: str = None, from_user_id: int = 123) -> MagicMock:
    """Создаёт мок объекта сообщения."""
    message = MagicMock()
    message.text = text
    message.from_user = MagicMock(id=from_user_id)
    message.chat = MagicMock(id=456)
    message.answer = AsyncMock()
    return message


async def _create_active_duel(session, telegram_user_id: int) -> Duel:
    """Создаёт активный поединок для пользователя."""
    scenario = Scenario(
        code=f"test_duel_scenario_{telegram_user_id}",
        title="Тестовый сценарий для дуэли",
        description="Описание",
        category="test",
        difficulty="normal",
        role_a_name="Роль A",
        role_a_goal="Цель A",
        role_b_name="Роль B",
        role_b_goal="Цель B",
        opening_line_a="Реплика A",
        opening_line_b="Реплика B",
        is_active=True,
    )
    session.add(scenario)
    await session.flush()

    duel_service = DuelService()
    duel = await duel_service.create_duel(session, telegram_user_id=telegram_user_id, scenario=scenario)
    return duel


class TestScenarioButtonFix:
    """Тесты для фикса кнопки '🎯 Сценарии'."""

    @pytest.mark.asyncio
    async def test_scenario_button_shows_picker_when_no_duel(self, fresh_test_db) -> None:
        """Кнопка '🎯 Сценарии' показывает список сценариев когда нет активного поединка."""
        from app.bot.handlers.menu import handle_start_button, START_BUTTON
        
        async with db_session.AsyncSessionLocal() as session:
            await _create_test_scenarios(session)
        
        message = _create_mock_message(text=START_BUTTON, from_user_id=123)
        
        with patch("app.bot.handlers.menu._send_scenario_picker") as mock_picker:
            await handle_start_button(message)
            mock_picker.assert_called_once()
            message.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_scenario_button_shows_picker_with_active_duel(self, fresh_test_db) -> None:
        """
        Кнопка '🎯 Сценарии' показывает список сценариев даже при активном поединке.
        
        Это основной тест для бага: раньше показывало "Поединок уже идёт...",
        теперь должен показывать список сценариев.
        """
        from app.bot.handlers.menu import handle_start_button, START_BUTTON
        
        async with db_session.AsyncSessionLocal() as session:
            await _create_test_scenarios(session)
            await _create_active_duel(session, telegram_user_id=123)
        
        message = _create_mock_message(text=START_BUTTON, from_user_id=123)
        
        with patch("app.bot.handlers.menu._send_scenario_picker") as mock_picker:
            await handle_start_button(message)
            
            # Проверяем что вызван scenario picker, а не show_main_menu
            mock_picker.assert_called_once()
            message.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_command_shows_menu_with_active_duel(self, fresh_test_db) -> None:
        """
        Команда /start показывает главное меню с состоянием поединка.
        
        Это отдельное поведение - /start должен показывать текущее состояние,
        а кнопка "🎯 Сценарии" должна показывать список сценариев.
        """
        from app.bot.handlers.menu import handle_start_command
        
        async with db_session.AsyncSessionLocal() as session:
            await _create_active_duel(session, telegram_user_id=123)
        
        message = _create_mock_message(text="/start", from_user_id=123)
        
        with patch("app.bot.handlers.menu.show_main_menu") as mock_menu:
            await handle_start_command(message)
            mock_menu.assert_called_once()


async def _create_test_scenarios(session, count=5) -> list:
    """Создаёт тестовые сценарии."""
    scenarios = []
    for i in range(count):
        scenario = Scenario(
            code=f"test_scenario_{i+1}",
            title=f"Тестовый сценарий {i+1}",
            description=f"Описание тестового сценария {i+1}",
            category="test",
            difficulty="normal",
            role_a_name=f"Роль A{i+1}",
            role_a_goal=f"Цель A{i+1}",
            role_b_name=f"Роль B{i+1}",
            role_b_goal=f"Цель B{i+1}",
            opening_line_a=f"Реплика A{i+1}",
            opening_line_b=f"Реплика B{i+1}",
            is_active=True,
        )
        session.add(scenario)
        scenarios.append(scenario)
    
    await session.flush()
    return scenarios
