"""
Duel Creation Flow Tests

Проверяет:
- Create duel from scenario picker
- Create duel from custom scenario
- Duel initialization (rounds, roles, status)
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB_PATH = ROOT / "data" / "agonarena_test_duel_creation.db"
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

import app.config as app_config  # noqa: E402
from app.db import session as db_session  # noqa: E402
from app.db.init_db import init_db  # noqa: E402
from app.services.duel_service import DuelService  # noqa: E402
from app.services.scenario_service import ScenarioService  # noqa: E402
from app.db.models.scenario import Scenario  # noqa: E402

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


async def _create_test_scenario(session) -> Scenario:
    """Создаёт тестовый сценарий."""
    scenario = Scenario(
        code="test_scenario",
        title="Тестовый сценарий",
        description="Описание для тестов",
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
    return scenario


class TestDuelFromScenarioPicker:
    """Тесты создания дуэли через выбор сценария."""

    @pytest.mark.asyncio
    async def test_create_duel_from_scenario_picker(self, fresh_test_db) -> None:
        """Создание дуэли из выбора сценария работает корректно."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            
            duel = await DuelService().create_duel(
                session, 
                telegram_user_id=123, 
                scenario=scenario
            )

            assert duel.id is not None
            assert duel.user_telegram_id == 123
            assert duel.scenario_id == scenario.id
            assert duel.status == "round_1_active"
            assert duel.current_round_number >= 0

    @pytest.mark.asyncio
    async def test_duel_initialization_sets_correct_roles(self, fresh_test_db) -> None:
        """Инициализация дуэли устанавливает правильные роли."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            
            duel = await DuelService().create_duel(
                session, 
                telegram_user_id=456, 
                scenario=scenario
            )
            
            # Проверяем, что раунды созданы
            rounds = await DuelService().get_duel_rounds(session, duel.id)
            
            assert len(rounds) == 2
            assert rounds[0].user_role != rounds[1].user_role  # Роли должны отличаться
            assert rounds[0].ai_role != rounds[1].ai_role      # Роли должны отличаться

    @pytest.mark.asyncio
    async def test_duel_has_correct_initial_status(self, fresh_test_db) -> None:
        """Дуэль после создания имеет статус round_1_active."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            
            duel = await DuelService().create_duel(
                session, 
                telegram_user_id=789, 
                scenario=scenario
            )

            assert duel.status == "round_1_active"


class TestDuelFromCustomScenario:
    """Тесты создания дуэли с кастомным сценарием."""

    @pytest.mark.asyncio
    async def test_create_duel_from_custom_scenario(self, fresh_test_db) -> None:
        """Создание дуэли с кастомным сценарием работает корректно."""
        async with db_session.AsyncSessionLocal() as session:
            # Создаём кастомный сценарий
            custom_scenario = Scenario(
                code="custom_123",
                title="Кастомный сценарий",
                description="Кастомное описание",
                category="custom",
                difficulty="normal",
                role_a_name="Кастомная роль A",
                role_a_goal="Цель кастомной роли A",
                role_b_name="Кастомная роль B",
                role_b_goal="Цель кастомной роли B",
                opening_line_a="Кастомная реплика A",
                opening_line_b="Кастомная реплика B",
                is_active=True,
            )
            session.add(custom_scenario)
            await session.flush()

            duel = await DuelService().create_duel(
                session, 
                telegram_user_id=999, 
                scenario=custom_scenario
            )

            assert duel.id is not None
            assert duel.user_telegram_id == 999
            assert duel.scenario_id == custom_scenario.id
            assert duel.status == "round_1_active"

    @pytest.mark.asyncio
    async def test_custom_scenario_preserves_all_attributes(self, fresh_test_db) -> None:
        """Кастомный сценарий сохраняет все свои атрибуты в дуэли."""
        async with db_session.AsyncSessionLocal() as session:
            custom_scenario = Scenario(
                code="custom_test",
                title="Тест кастома",
                description="Тестовое описание кастома",
                category="custom",
                difficulty="hard",
                role_a_name="Менеджер проекта",
                role_a_goal="Убедить команду в необходимости срочного релиза",
                role_b_name="Разработчик",
                role_b_goal="Отстоять необходимость дополнительного времени на тестирование",
                opening_line_a="Коллеги, мы должны выпустить продукт к концу месяца!",
                opening_line_b="Я понимаю важность, но качество тоже важно.",
                is_active=True,
            )
            session.add(custom_scenario)
            await session.flush()

            duel = await DuelService().create_duel(
                session, 
                telegram_user_id=111, 
                scenario=custom_scenario
            )
            
            # Проверяем, что раунды созданы с правильными ролями
            rounds = await DuelService().get_duel_rounds(session, duel.id)
            
            # В первом раунде пользователь получает роль A, AI - роль B
            assert rounds[0].user_role == custom_scenario.role_a_name
            assert rounds[0].ai_role == custom_scenario.role_b_name
            
            # Во втором раунде роли меняются местами
            assert rounds[1].user_role == custom_scenario.role_b_name
            assert rounds[1].ai_role == custom_scenario.role_a_name


class TestDuelInitialization:
    """Тесты инициализации дуэли."""

    @pytest.mark.asyncio
    async def test_duel_initializes_with_two_rounds(self, fresh_test_db) -> None:
        """При создании дуэли создаются два раунда."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            
            duel = await DuelService().create_duel(
                session, 
                telegram_user_id=222, 
                scenario=scenario
            )
            
            rounds = await DuelService().get_duel_rounds(session, duel.id)
            
            assert len(rounds) == 2
            assert rounds[0].round_number == 1
            assert rounds[1].round_number == 2

    @pytest.mark.asyncio
    async def test_duel_rounds_have_correct_status_after_creation(self, fresh_test_db) -> None:
        """После создания раунды имеют статус pending."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            
            duel = await DuelService().create_duel(
                session, 
                telegram_user_id=333, 
                scenario=scenario
            )
            
            rounds = await DuelService().get_duel_rounds(session, duel.id)
            
            assert rounds[0].status == "pending"
            assert rounds[1].status == "pending"

    @pytest.mark.asyncio
    async def test_duel_initializes_with_correct_time_limits(self, fresh_test_db) -> None:
        """Дуэль инициализируется с корректными временными лимитами."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            
            duel = await DuelService().create_duel(
                session, 
                telegram_user_id=444, 
                scenario=scenario
            )
            
            # Проверяем, что у дуэли установлено время на ход
            assert duel.turn_time_limit_sec > 0

    @pytest.mark.asyncio
    async def test_duel_initializes_with_correct_scenario_data(self, fresh_test_db) -> None:
        """Дуэль правильно инициализируется данными сценария."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            
            duel = await DuelService().create_duel(
                session, 
                telegram_user_id=555, 
                scenario=scenario
            )
            
            assert duel.scenario_id == scenario.id
            # Проверяем, что данные сценария доступны через дуэль
            assert duel.user_role_round1 == scenario.role_a_name
            assert duel.ai_role_round1 == scenario.role_b_name
            assert duel.user_role_round2 == scenario.role_b_name
            assert duel.ai_role_round2 == scenario.role_a_name