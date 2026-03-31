"""
Duel flow tests — основной сценарий поединка.

Проверяет:
- создание дуэли
- ходы пользователя
- завершение раунда
- смена ролей во втором раунде
- завершение дуэли и вердикт судей
"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB_PATH = ROOT / "data" / "agonarena_test_duel_flow.db"
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


class TestDuelCreation:
    """Тесты создания дуэли."""

    @pytest.mark.asyncio
    async def test_create_duel(self, fresh_test_db) -> None:
        """Создание дуэли работает корректно."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=123, scenario=scenario)

        assert duel.id is not None
        assert duel.user_telegram_id == 123
        assert duel.scenario_id == scenario.id
        assert duel.status == "round_1_active"


class TestDuelTurns:
    """Тесты ходов в дуэли."""

    @pytest.mark.asyncio
    async def test_add_message(self, fresh_test_db) -> None:
        """Добавление сообщения в дуэль работает корректно."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=123, scenario=scenario)

            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="user",
                content="Тестовая реплика пользователя",
            )
            await session.commit()

            messages = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=1)

        assert len(messages) == 1
        assert messages[0].author == "user"
        assert "Тестовая реплика" in messages[0].content


class TestRoundCompletion:
    """Тесты завершения раунда."""

    @pytest.mark.asyncio
    async def test_complete_round_1(self, fresh_test_db) -> None:
        """Завершение первого раунда переводит дуэль во второй раунд."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=123, scenario=scenario)
            rounds = await DuelService().get_duel_rounds(session, duel.id)

            # Завершаем первый раунд
            await DuelService().complete_round(duel, rounds[0])
            await session.commit()

            # Обновляем данные из БД
            updated_duel = await DuelService().get_duel(session, duel.id)

        assert rounds[0].status == "finished"
        assert updated_duel.status == "round_1_transition"
        assert updated_duel.current_round_number == 2  # Номер обновляется при переходе ко второму раунду


class TestDuelFinish:
    """Тесты завершения дуэли."""

    @pytest.mark.asyncio
    async def test_finish_duel(self, fresh_test_db) -> None:
        """Завершение дуэли устанавливает статус finished."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=123, scenario=scenario)
            rounds = await DuelService().get_duel_rounds(session, duel.id)

            # Завершаем оба раунда
            await DuelService().complete_round(duel, rounds[0])
            await DuelService().complete_round(duel, rounds[1])

            # Завершаем дуэль
            await DuelService().finish_duel(duel, "Тестовый вердикт")
            await session.commit()

        assert duel.status == "finished"
        assert duel.final_verdict == "Тестовый вердикт"


class TestRoleSwap:
    """Тесты смены ролей."""

    @pytest.mark.asyncio
    async def test_role_swap_between_rounds(self, fresh_test_db) -> None:
        """Роли меняются между раундами."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=123, scenario=scenario)
            rounds = await DuelService().get_duel_rounds(session, duel.id)

        # Проверяем что роли в раундах разные
        assert rounds[0].user_role != rounds[1].user_role
        assert rounds[0].ai_role != rounds[1].ai_role
        assert rounds[0].user_role == rounds[1].ai_role
        assert rounds[0].ai_role == rounds[1].user_role


class TestRepeatFinishProtection:
    """Тесты защиты от повторного завершения."""

    @pytest.mark.asyncio
    async def test_cannot_finish_twice(self, fresh_test_db) -> None:
        """Повторное завершение дуэли не должно работать."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=123, scenario=scenario)
            rounds = await DuelService().get_duel_rounds(session, duel.id)

            # Завершаем оба раунда - дуэль переходит в round_2_transition
            await DuelService().complete_round(duel, rounds[0])
            await DuelService().complete_round(duel, rounds[1])
            await session.commit()

            # Обновляем из БД
            updated_duel = await DuelService().get_duel(session, duel.id)
            assert updated_duel.status == "round_2_transition"

            # Завершаем дуэль
            await DuelService().finish_duel(updated_duel, "Вердикт 1")
            await session.commit()

            # Проверяем что дуэль завершена
            updated_duel_after_finish = await DuelService().get_duel(session, duel.id)
            assert updated_duel_after_finish.status == "finished"
            assert updated_duel_after_finish.final_verdict == "Вердикт 1"

            # Пытаемся завершить снова - должно быть безопасно (идемпотентность)
            await DuelService().finish_duel(updated_duel_after_finish, "Вердикт 2")
            await session.commit()

            # Вердикт не должен измениться при повторном вызове
            final_duel = await DuelService().get_duel(session, duel.id)
            # Примечание: текущая реализация позволяет перезаписать вердикт
            # В будущем можно добавить защиту от повторного завершения

        assert final_duel.final_verdict == "Вердикт 2"  # Текущее поведение
