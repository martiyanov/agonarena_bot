"""
Duel Turns Flow Tests

Проверяет:
- User text message in round 1
- User text message in round 2
- AI response generation
- Message history tracking
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB_PATH = ROOT / "data" / "agonarena_test_duel_turns.db"
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

import app.config as app_config  # noqa: E402
from app.db import session as db_session  # noqa: E402
from app.db.init_db import init_db  # noqa: E402
from app.services.duel_service import DuelService  # noqa: E402
from app.services.scenario_service import ScenarioService  # noqa: E402
from app.db.models.scenario import Scenario  # noqa: E402
from app.db.models.message import DuelMessage  # noqa: E402

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


class TestUserTextMessageRound1:
    """Тесты текстового сообщения пользователя в раунде 1."""

    @pytest.mark.asyncio
    async def test_user_text_message_in_round_1(self, fresh_test_db) -> None:
        """Текстовое сообщение пользователя в раунде 1 сохраняется корректно."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=123, scenario=scenario)
            
            # Добавляем сообщение пользователя в раунде 1
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="user",
                content="Тестовое сообщение пользователя в раунде 1"
            )
            await session.commit()

            messages = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=1)

        assert len(messages) == 1
        assert messages[0].author == "user"
        assert messages[0].content == "Тестовое сообщение пользователя в раунде 1"
        assert messages[0].round_number == 1

    @pytest.mark.asyncio
    async def test_multiple_user_messages_in_round_1(self, fresh_test_db) -> None:
        """Несколько сообщений пользователя в раунде 1 сохраняются корректно."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=456, scenario=scenario)
            
            # Добавляем несколько сообщений пользователя в раунде 1
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="user",
                content="Первое сообщение пользователя"
            )
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="user",
                content="Второе сообщение пользователя"
            )
            await session.commit()

            messages = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=1)

        assert len(messages) == 2
        assert messages[0].content == "Первое сообщение пользователя"
        assert messages[1].content == "Второе сообщение пользователя"

    @pytest.mark.asyncio
    async def test_user_message_timestamp_in_round_1(self, fresh_test_db) -> None:
        """Сообщения пользователя в раунде 1 имеют корректные временные метки."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=789, scenario=scenario)
            
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="user",
                content="Сообщение с временной меткой"
            )
            await session.commit()

            messages = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=1)

        assert len(messages) == 1
        assert messages[0].created_at is not None


class TestUserTextMessageRound2:
    """Тесты текстового сообщения пользователя в раунде 2."""

    @pytest.mark.asyncio
    async def test_user_text_message_in_round_2(self, fresh_test_db) -> None:
        """Текстовое сообщение пользователя в раунде 2 сохраняется корректно."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=234, scenario=scenario)
            
            # Добавляем сообщение пользователя в раунде 2
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=2,
                author="user",
                content="Тестовое сообщение пользователя в раунде 2"
            )
            await session.commit()

            messages = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=2)

        assert len(messages) == 1
        assert messages[0].author == "user"
        assert messages[0].content == "Тестовое сообщение пользователя в раунде 2"
        assert messages[0].round_number == 2

    @pytest.mark.asyncio
    async def test_separate_message_history_per_round(self, fresh_test_db) -> None:
        """История сообщений отдельная для каждого раунда."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=345, scenario=scenario)
            
            # Добавляем сообщения в разных раундах
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="user",
                content="Сообщение в раунде 1"
            )
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=2,
                author="user",
                content="Сообщение в раунде 2"
            )
            await session.commit()

            messages_r1 = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=1)
            messages_r2 = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=2)

        assert len(messages_r1) == 1
        assert len(messages_r2) == 1
        assert messages_r1[0].content == "Сообщение в раунде 1"
        assert messages_r2[0].content == "Сообщение в раунде 2"

    @pytest.mark.asyncio
    async def test_user_can_send_messages_in_both_rounds(self, fresh_test_db) -> None:
        """Пользователь может отправлять сообщения в обоих раундах."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=456, scenario=scenario)
            
            # Сообщения в раунде 1
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="user",
                content="Сообщение в раунде 1, шаг 1"
            )
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="user",
                content="Сообщение в раунде 1, шаг 2"
            )
            
            # Сообщения в раунде 2
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=2,
                author="user",
                content="Сообщение в раунде 2, шаг 1"
            )
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=2,
                author="user",
                content="Сообщение в раунде 2, шаг 2"
            )
            await session.commit()

            messages_r1 = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=1)
            messages_r2 = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=2)

        assert len(messages_r1) == 2
        assert len(messages_r2) == 2
        assert messages_r1[0].content == "Сообщение в раунде 1, шаг 1"
        assert messages_r1[1].content == "Сообщение в раунде 1, шаг 2"
        assert messages_r2[0].content == "Сообщение в раунде 2, шаг 1"
        assert messages_r2[1].content == "Сообщение в раунде 2, шаг 2"


class TestAIResponseGeneration:
    """Тесты генерации ответов AI."""

    @pytest.mark.asyncio
    async def test_ai_response_saved_correctly(self, fresh_test_db) -> None:
        """AI-ответ сохраняется корректно с указанием автора."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=567, scenario=scenario)
            
            # Добавляем AI-ответ в раунде 1
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="ai",
                content="AI-ответ в раунде 1"
            )
            await session.commit()

            messages = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=1)

        assert len(messages) == 1
        assert messages[0].author == "ai"
        assert messages[0].content == "AI-ответ в раунде 1"

    @pytest.mark.asyncio
    async def test_ai_and_user_messages_coexist(self, fresh_test_db) -> None:
        """AI и пользовательские сообщения могут сосуществовать в одном раунде."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=678, scenario=scenario)
            
            # Добавляем сообщения от обоих участников
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="user",
                content="Сообщение пользователя"
            )
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="ai",
                content="Сообщение AI"
            )
            await session.commit()

            messages = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=1)

        assert len(messages) == 2
        user_msg = next((m for m in messages if m.author == "user"), None)
        ai_msg = next((m for m in messages if m.author == "ai"), None)
        
        assert user_msg is not None
        assert ai_msg is not None
        assert user_msg.content == "Сообщение пользователя"
        assert ai_msg.content == "Сообщение AI"

    @pytest.mark.asyncio
    async def test_ai_response_in_both_rounds(self, fresh_test_db) -> None:
        """AI может отвечать в обоих раундах."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=789, scenario=scenario)
            
            # AI-ответы в обоих раундах
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="ai",
                content="AI-ответ в раунде 1"
            )
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=2,
                author="ai",
                content="AI-ответ в раунде 2"
            )
            await session.commit()

            messages_r1 = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=1)
            messages_r2 = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=2)

        assert len(messages_r1) == 1
        assert len(messages_r2) == 1
        assert messages_r1[0].content == "AI-ответ в раунде 1"
        assert messages_r2[0].content == "AI-ответ в раунде 2"


class TestMessageHistoryTracking:
    """Тесты отслеживания истории сообщений."""

    @pytest.mark.asyncio
    async def test_get_all_messages_for_duel(self, fresh_test_db) -> None:
        """Получение всех сообщений для дуэли."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=890, scenario=scenario)
            
            # Добавляем сообщения в обоих раундах
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="user",
                content="Сообщение в раунде 1"
            )
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=2,
                author="user",
                content="Сообщение в раунде 2"
            )
            await session.commit()

            # Get messages from both rounds separately
            messages_r1 = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=1)
            messages_r2 = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=2)
            all_messages = messages_r1 + messages_r2

        assert len(all_messages) == 2
        assert any(m.content == "Сообщение в раунде 1" for m in all_messages)
        assert any(m.content == "Сообщение в раунде 2" for m in all_messages)

    @pytest.mark.asyncio
    async def test_messages_ordered_by_timestamp(self, fresh_test_db) -> None:
        """Сообщения возвращаются в порядке их создания."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=901, scenario=scenario)
            
            # Добавляем сообщения в определенном порядке
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="user",
                content="Первое сообщение"
            )
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="ai",
                content="Второе сообщение"
            )
            await session.commit()

            messages = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=1)

        assert len(messages) == 2
        # Первое сообщение от пользователя, второе от AI
        assert messages[0].content == "Первое сообщение"
        assert messages[1].content == "Второе сообщение"

    @pytest.mark.asyncio
    async def test_message_history_preserves_authors(self, fresh_test_db) -> None:
        """История сообщений сохраняет информацию об авторах."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=12, scenario=scenario)
            
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="user",
                content="Пользовательское сообщение"
            )
            await DuelService().add_message(
                session,
                duel_id=duel.id,
                round_number=1,
                author="ai",
                content="AI-сообщение"
            )
            await session.commit()

            messages = await DuelService().list_messages_for_round(session, duel_id=duel.id, round_number=1)

        user_msg = next((m for m in messages if m.author == "user"), None)
        ai_msg = next((m for m in messages if m.author == "ai"), None)
        
        assert user_msg is not None
        assert ai_msg is not None
        assert user_msg.author == "user"
        assert ai_msg.author == "ai"

    @pytest.mark.asyncio
    async def test_clear_message_history_if_needed(self, fresh_test_db) -> None:
        """Проверяем, что история сообщений не переплетается между дуэлями."""
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            
            # Создаем две дуэли
            duel1 = await DuelService().create_duel(session, telegram_user_id=111, scenario=scenario)
            duel2 = await DuelService().create_duel(session, telegram_user_id=222, scenario=scenario)
            
            # Добавляем сообщения в первую дуэль
            await DuelService().add_message(
                session,
                duel_id=duel1.id,
                round_number=1,
                author="user",
                content="Сообщение в дуэли 1"
            )
            # Добавляем сообщения во вторую дуэль
            await DuelService().add_message(
                session,
                duel_id=duel2.id,
                round_number=1,
                author="user",
                content="Сообщение в дуэли 2"
            )
            await session.commit()

            messages_duel1 = await DuelService().list_messages_for_round(session, duel_id=duel1.id, round_number=1)
            messages_duel2 = await DuelService().list_messages_for_round(session, duel_id=duel2.id, round_number=1)

        assert len(messages_duel1) == 1
        assert len(messages_duel2) == 1
        assert messages_duel1[0].content == "Сообщение в дуэли 1"
        assert messages_duel2[0].content == "Сообщение в дуэли 2"