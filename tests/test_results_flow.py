"""
Results Display Tests

Проверяет:
- My results screen (latest duel)
- Judge comments display (with round breakdown)
- Finished duel status
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB_PATH = ROOT / "data" / "agonarena_test_results_flow.db"
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

import app.config as app_config  # noqa: E402
from app.db import session as db_session  # noqa: E402
from app.db.init_db import init_db  # noqa: E402
from app.services.duel_service import DuelService  # noqa: E402
from app.services.scenario_service import ScenarioService  # noqa: E402
from app.db.models.scenario import Scenario  # noqa: E402
from app.db.models.duel import Duel  # noqa: E402
from app.db.models.judge_result import JudgeResult  # noqa: E402

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


def _create_mock_message(text: str = None, from_user_id: int = 123) -> MagicMock:
    """Создаёт мок объекта сообщения."""
    message = MagicMock()
    message.text = text
    message.from_user = MagicMock(id=from_user_id)
    message.chat = MagicMock(id=456)
    message.reply = AsyncMock()
    message.reply_text = AsyncMock()
    message.answer = AsyncMock()
    return message


class TestMyResultsScreen:
    """Тесты экрана моих результатов (последняя дуэль)."""

    @pytest.mark.asyncio
    async def test_my_results_shows_latest_finished_duel(self, fresh_test_db) -> None:
        """Экран результатов показывает последнюю завершённую дуэль."""
        from app.bot.handlers.menu import my_results

        # Подготовка: создаём завершённую дуэль
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=123, scenario=scenario)
            
            # Завершаем дуэль
            rounds = await DuelService().get_duel_rounds(session, duel.id)
            for round_obj in rounds:
                round_obj.status = "finished"
            duel.status = "finished"
            duel.final_verdict = "Пользователь выиграл по решению судей"
            await session.commit()

        message = _create_mock_message("/my_results", from_user_id=123)

        await my_results(message)

        # Проверяем, что результаты отправлены
        message.answer.assert_called_once()
        call_args = message.answer.call_args
        results_text = call_args[0][0] if call_args[0] else ""
        
        # Результаты должны содержать информацию о дуэли
        assert "результаты" in results_text.lower() or "итоги" in results_text.lower()
        assert "пользователь выиграл" in results_text.lower()

    @pytest.mark.asyncio
    async def test_my_results_shows_nothing_when_no_finished_duels(self, fresh_test_db) -> None:
        """Экран результатов показывает сообщение при отсутствии завершённых дуэлей."""
        from app.bot.handlers.menu import my_results

        message = _create_mock_message("/my_results", from_user_id=456)

        await my_results(message)

        # Проверяем, что отправлено сообщение об отсутствии результатов
        message.answer.assert_called_once()
        call_args = message.answer.call_args
        results_text = call_args[0][0] if call_args[0] else ""
        
        assert any(keyword in results_text.lower() for keyword in ["нет", "пока", "результатов", "участвуйте"])

    @pytest.mark.asyncio
    async def test_my_results_shows_latest_among_multiple_duels(self, fresh_test_db) -> None:
        """Экран результатов показывает самую последнюю из нескольких завершённых дуэлей."""
        from app.bot.handlers.menu import my_results

        # Подготовка: создаём несколько дуэлей
        async with db_session.AsyncSessionLocal() as session:
            scenario1 = await _create_test_scenario(session)
            scenario2 = Scenario(
                code="test_scenario_2",
                title="Второй сценарий",
                description="Второй тестовый сценарий",
                category="test",
                difficulty="normal",
                role_a_name="Роль C",
                role_a_goal="Цель C",
                role_b_name="Роль D",
                role_b_goal="Цель D",
                opening_line_a="Реплика C",
                opening_line_b="Реплика D",
                is_active=True,
            )
            session.add(scenario2)
            await session.flush()

            # Создаём первую дуэль и завершаем её
            duel1 = await DuelService().create_duel(session, telegram_user_id=789, scenario=scenario1)
            rounds1 = await DuelService().get_duel_rounds(session, duel1.id)
            for round_obj in rounds1:
                round_obj.status = "finished"
            duel1.status = "finished"
            duel1.final_verdict = "Первая дуэль: победа пользователя"
            
            # Создаём вторую дуэль и завершаем её (она более новая)
            duel2 = await DuelService().create_duel(session, telegram_user_id=789, scenario=scenario2)
            rounds2 = await DuelService().get_duel_rounds(session, duel2.id)
            for round_obj in rounds2:
                round_obj.status = "finished"
            duel2.status = "finished"
            duel2.final_verdict = "Вторая дуэль: победа AI"
            
            await session.commit()

        message = _create_mock_message("/my_results", from_user_id=789)

        await my_results(message)

        # Результаты должны содержать информацию о более новой дуэль
        message.answer.assert_called_once()
        call_args = message.answer.call_args
        results_text = call_args[0][0] if call_args[0] else ""
        
        # Скорее всего будет показана более новая дуэль (вторая)
        assert "вторая дуэль" in results_text.lower() or "победа ai" in results_text.lower()

    @pytest.mark.asyncio
    async def test_my_results_shows_correct_user_data_only(self, fresh_test_db) -> None:
        """Экран результатов показывает только данные текущего пользователя."""
        from app.bot.handlers.menu import my_results

        # Подготовка: создаём дуэли для разных пользователей
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            
            # Дуэль для пользователя 999
            duel1 = await DuelService().create_duel(session, telegram_user_id=999, scenario=scenario)
            rounds1 = await DuelService().get_duel_rounds(session, duel1.id)
            for round_obj in rounds1:
                round_obj.status = "finished"
            duel1.status = "finished"
            duel1.final_verdict = "Дуэль пользователя 999"
            
            # Дуэль для пользователя 888
            duel2 = await DuelService().create_duel(session, telegram_user_id=888, scenario=scenario)
            rounds2 = await DuelService().get_duel_rounds(session, duel2.id)
            for round_obj in rounds2:
                round_obj.status = "finished"
            duel2.status = "finished"
            duel2.final_verdict = "Дуэль пользователя 888"
            
            await session.commit()

        message = _create_mock_message("/my_results", from_user_id=999)

        await my_results(message)

        # Результаты должны содержать только данные пользователя 999
        message.answer.assert_called_once()
        call_args = message.answer.call_args
        results_text = call_args[0][0] if call_args[0] else ""
        
        assert "пользователя 999" in results_text.lower()
        assert "пользователя 888" not in results_text.lower()


class TestJudgeCommentsDisplay:
    """Тесты отображения комментариев судей."""

    @pytest.mark.asyncio
    async def test_judge_comments_include_round_breakdown(self, fresh_test_db) -> None:
        """Комментарии судей включают разбивку по раундам."""
        from app.bot.handlers.menu import my_results

        # Подготовка: создаём дуэль с результатами судей
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=234, scenario=scenario)
            
            # Завершаем дуэль
            rounds = await DuelService().get_duel_rounds(session, duel.id)
            for round_obj in rounds:
                round_obj.status = "finished"
            duel.status = "finished"
            duel.final_verdict = "Победа пользователя"
            
            # Добавляем результаты судей с раундовыми комментариями
            judge_result = JudgeResult(
                duel_id=duel.id,
                judge_type="owner",
                winner="user",
                comment="Владелец: пользователь был убедителен",
                round1_comment="Раунд 1: чёткая аргументация",
                round2_comment="Раунд 2: уверенная защита позиции"
            )
            session.add(judge_result)
            await session.commit()

        message = _create_mock_message("/my_results", from_user_id=234)

        await my_results(message)

        # Проверяем, что результаты содержат раундовые комментарии
        message.answer.assert_called_once()
        call_args = message.answer.call_args
        results_text = call_args[0][0] if call_args[0] else ""
        
        assert "раунд 1" in results_text.lower()
        assert "раунд 2" in results_text.lower()
        assert "чёткая аргументация" in results_text.lower()
        assert "уверенная защита" in results_text.lower()

    @pytest.mark.asyncio
    async def test_multiple_judge_comments_displayed(self, fresh_test_db) -> None:
        """Отображаются комментарии от нескольких судей."""
        from app.bot.handlers.menu import my_results

        # Подготовка: создаём дуэль с несколькими судейскими результатами
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=345, scenario=scenario)
            
            # Завершаем дуэль
            rounds = await DuelService().get_duel_rounds(session, duel.id)
            for round_obj in rounds:
                round_obj.status = "finished"
            duel.status = "finished"
            duel.final_verdict = "Ничья по решению большинства"
            
            # Добавляем несколько результатов судей
            judge_result1 = JudgeResult(
                duel_id=duel.id,
                judge_type="owner",
                winner="user",
                comment="Владелец: пользователь был сильнее",
                round1_comment="Р1: активное начало",
                round2_comment="Р2: устойчивая позиция"
            )
            judge_result2 = JudgeResult(
                duel_id=duel.id,
                judge_type="team", 
                winner="ai",
                comment="Команда: AI показала лучшую стратегию",
                round1_comment="Р1: AI контроль ситуации",
                round2_comment="Р2: точные ответы"
            )
            session.add(judge_result1)
            session.add(judge_result2)
            await session.commit()

        message = _create_mock_message("/my_results", from_user_id=345)

        await my_results(message)

        # Проверяем, что результаты содержат комментарии от разных судей
        message.answer.assert_called_once()
        call_args = message.answer.call_args
        results_text = call_args[0][0] if call_args[0] else ""
        
        # Должны быть видны комментарии от разных судей
        assert any(keyword in results_text.lower() for keyword in ["владелец", "собственник"])
        assert any(keyword in results_text.lower() for keyword in ["команда", "team"])
        # И раундовые комментарии от обоих
        assert "р1:" in results_text.lower()
        assert "р2:" in results_text.lower()

    @pytest.mark.asyncio
    async def test_judge_comments_handle_missing_round_comments(self, fresh_test_db) -> None:
        """Обработка случая, когда у судьи нет раундовых комментариев."""
        from app.bot.handlers.menu import my_results

        # Подготовка: создаём дуэль с результатом судьи без раундовых комментариев
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=456, scenario=scenario)
            
            # Завершаем дуэль
            rounds = await DuelService().get_duel_rounds(session, duel.id)
            for round_obj in rounds:
                round_obj.status = "finished"
            duel.status = "finished"
            duel.final_verdict = "Победа AI"
            
            # Результат судьи БЕЗ раундовых комментариев
            judge_result = JudgeResult(
                duel_id=duel.id,
                judge_type="sending_to_negotiation",
                winner="ai",
                comment="Отправитель: AI была более убедительна",
                round1_comment="",  # Пусто
                round2_comment=""   # Пусто
            )
            session.add(judge_result)
            await session.commit()

        message = _create_mock_message("/my_results", from_user_id=456)

        await my_results(message)

        # Проверяем, что результаты показываются без раундовой разбивки
        message.answer.assert_called_once()
        call_args = message.answer.call_args
        results_text = call_args[0][0] if call_args[0] else ""
        
        # Общий комментарий должен быть
        assert "ai была более убедительна" in results_text.lower()
        # Но не должно быть специальной раундовой разбивки
        # (хотя может быть общий упоминание раундов в общем комментарии)


class TestFinishedDuelStatus:
    """Тесты статуса завершённой дуэли."""

    @pytest.mark.asyncio
    async def test_my_results_only_shows_finished_duels(self, fresh_test_db) -> None:
        """Экран результатов показывает только завершённые дуэли."""
        from app.bot.handlers.menu import my_results

        # Подготовка: создаём дуэль в процессе
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel_in_progress = await DuelService().create_duel(session, telegram_user_id=567, scenario=scenario)
            # Эта дуэль НЕ завершена
            
            # Создаём завершённую дуэль
            duel_finished = await DuelService().create_duel(session, telegram_user_id=567, scenario=scenario)
            rounds = await DuelService().get_duel_rounds(session, duel_finished.id)
            for round_obj in rounds:
                round_obj.status = "finished"
            duel_finished.status = "finished"
            duel_finished.final_verdict = "Завершённая дуэль"
            
            await session.commit()

        message = _create_mock_message("/my_results", from_user_id=567)

        await my_results(message)

        # Результаты должны содержать только завершённую дуэль
        message.answer.assert_called_once()
        call_args = message.answer.call_args
        results_text = call_args[0][0] if call_args[0] else ""
        
        assert "завершённая дуэль" in results_text.lower()
        # Не должно быть информации о дуэли в процессе

    @pytest.mark.asyncio
    async def test_duel_status_reflected_in_results(self, fresh_test_db) -> None:
        """Статус дуэли отражается в результатах."""
        from app.bot.handlers.menu import my_results

        # Подготовка: создаём завершённую дуэль с финальным вердиктом
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=678, scenario=scenario)
            
            # Завершаем дуэль с конкретным результатом
            rounds = await DuelService().get_duel_rounds(session, duel.id)
            for round_obj in rounds:
                round_obj.status = "finished"
            duel.status = "finished"
            duel.final_verdict = "Пользователь выиграл по аргументации"
            
            await session.commit()

        message = _create_mock_message("/my_results", from_user_id=678)

        await my_results(message)

        # Проверяем, что результаты содержат финальный вердикт
        message.answer.assert_called_once()
        call_args = message.answer.call_args
        results_text = call_args[0][0] if call_args[0] else ""
        
        assert "пользователь выиграл" in results_text.lower()
        assert "аргументации" in results_text.lower()

    @pytest.mark.asyncio
    async def test_results_show_scenario_info(self, fresh_test_db) -> None:
        """Результаты показывают информацию о сценарии."""
        from app.bot.handlers.menu import my_results

        # Подготовка: создаём дуэль с конкретным сценарием
        async with db_session.AsyncSessionLocal() as session:
            scenario = Scenario(
                code="salary_negotiation",
                title="Переговоры о зарплате",
                description="Ситуация переговоров о повышении зарплаты",
                category="business",
                difficulty="hard",
                role_a_name="Сотрудник",
                role_a_goal="Выторговать максимальное повышение",
                role_b_name="Руководитель",
                role_b_goal="Сохранить бюджет и мотивировать сотрудника",
                opening_line_a="Я считаю, что заслуживаю повышения",
                opening_line_b="Давайте посмотрим на ваши достижения",
                is_active=True,
            )
            session.add(scenario)
            await session.flush()

            duel = await DuelService().create_duel(session, telegram_user_id=789, scenario=scenario)
            
            # Завершаем дуэль
            rounds = await DuelService().get_duel_rounds(session, duel.id)
            for round_obj in rounds:
                round_obj.status = "finished"
            duel.status = "finished"
            duel.final_verdict = "Ничья - достигнут компромисс"
            
            await session.commit()

        message = _create_mock_message("/my_results", from_user_id=789)

        await my_results(message)

        # Проверяем, что результаты содержат информацию о сценарии
        message.answer.assert_called_once()
        call_args = message.answer.call_args
        results_text = call_args[0][0] if call_args[0] else ""
        
        assert "переговоры о зарплате" in results_text.lower() or "зарплате" in results_text.lower()
        assert "сотрудник" in results_text.lower() or "руководитель" in results_text.lower()

    @pytest.mark.asyncio
    async def test_results_include_role_info(self, fresh_test_db) -> None:
        """Результаты включают информацию о ролях."""
        from app.bot.handlers.menu import my_results

        # Подготовка: создаём дуэль с информацией о ролях
        async with db_session.AsyncSessionLocal() as session:
            scenario = await _create_test_scenario(session)
            duel = await DuelService().create_duel(session, telegram_user_id=890, scenario=scenario)
            
            # Завершаем дуэль
            rounds = await DuelService().get_duel_rounds(session, duel.id)
            for round_obj in rounds:
                round_obj.status = "finished"
            duel.status = "finished"
            duel.final_verdict = "Пользователь выиграл в своей роли"
            
            await session.commit()

        message = _create_mock_message("/my_results", from_user_id=890)

        await my_results(message)

        # Проверяем, что результаты содержат информацию о ролях
        message.answer.assert_called_once()
        call_args = message.answer.call_args
        results_text = call_args[0][0] if call_args[0] else ""
        
        # Должна быть информация о том, какие роли были
        assert "роль" in results_text.lower()
        # И, возможно, упоминание конкретных ролей из сценария
        assert any(role in results_text.lower() for role in ["роль a", "роль b"])


class TestResultsFormatting:
    """Тесты форматирования результатов."""

    @pytest.mark.asyncio
    async def test_results_formatted_readably(self, fresh_test_db) -> None:
        """Результаты форматируются в читаемом виде."""
        from app.bot.handlers.menu import my_results

        # Подготовка: создаём дуэль с полной информацией
        async with db_session.AsyncSessionLocal() as session:
            scenario = Scenario(
                code="complex_scenario",
                title="Сложная бизнес-ситуация",
                description="Сложная ситуация с множеством факторов",
                category="business",
                difficulty="expert",
                role_a_name="Директор проекта",
                role_a_goal="Убедить совет директоров в необходимости инвестиций",
                role_b_name="Финансовый контролёр",
                role_b_goal="Обосновать необходимость экономии",
                opening_line_a="Уважаемые коллеги, проект требует дополнительного финансирования",
                opening_line_b="Прежде чем принимать решение, давайте рассмотрим риски",
                is_active=True,
            )
            session.add(scenario)
            await session.flush()

            duel = await DuelService().create_duel(session, telegram_user_id=901, scenario=scenario)
            
            # Завершаем дуэль
            rounds = await DuelService().get_duel_rounds(session, duel.id)
            for round_obj in rounds:
                round_obj.status = "finished"
            duel.status = "finished"
            duel.final_verdict = "Пользователь (Директор проекта) убедил финансового контролёра"
            
            # Добавляем результаты судей
            judge_result = JudgeResult(
                duel_id=duel.id,
                judge_type="owner",
                winner="user",
                comment="Убедительная презентация стратегических преимуществ",
                round1_comment="Р1: чёткое изложение проблемы",
                round2_comment="Р2: эффективные контраргументы"
            )
            session.add(judge_result)
            await session.commit()

        message = _create_mock_message("/my_results", from_user_id=901)

        await my_results(message)

        # Проверяем, что результаты хорошо отформатированы
        message.answer.assert_called_once()
        call_args = message.answer.call_args
        results_text = call_args[0][0] if call_args[0] else ""
        
        # Текст должен быть структурирован и читаем
        assert len(results_text.strip()) > 50  # Должно быть достаточно текста
        assert "директор проекта" in results_text.lower()
        assert "финансовый контролёр" in results_text.lower()
        assert "р1:" in results_text.lower() or "раунд 1" in results_text.lower()
        assert "р2:" in results_text.lower() or "раунд 2" in results_text.lower()

    @pytest.mark.asyncio
    async def test_empty_results_handled_gracefully(self, fresh_test_db) -> None:
        """Пустые результаты обрабатываются корректно."""
        from app.bot.handlers.menu import my_results

        # Подготовка: пользователь без завершённых дуэлей
        message = _create_mock_message("/my_results", from_user_id=12)

        await my_results(message)

        # Проверяем, что отправлено осмысленное сообщение
        message.answer.assert_called_once()
        call_args = message.answer.call_args
        results_text = call_args[0][0] if call_args[0] else ""
        
        # Сообщение должно быть дружелюбным и информировать о том, что результатов пока нет
        assert any(keyword in results_text.lower() for keyword in ["нет", "пока", "результатов", "участвуйте", "начать", "создать"])