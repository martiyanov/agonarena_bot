"""
Judge Round Breakdown Tests

Проверяет:
- LLM response парсит round1_comment/round2_comment
- _format_final_verdict отображает разбивку по раундам
- my_results показывает round comments
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB_PATH = ROOT / "data" / "agonarena_test_judge.db"
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

from app.db import session as db_session
from app.db.init_db import init_db
from app.db.models import Duel, DuelRound, JudgeResult
from app.services.duel_service import DuelService
from app.services.judge_service import JudgeService, JudgeVerdict, JudgeContext


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


class TestJudgeServiceRoundComments:
    """Тесты извлечения round комментариев из LLM response."""

    @pytest.mark.asyncio
    async def test_run_single_judge_extracts_round_comments(self, fresh_test_db):
        """LLM response с round1_comment/round2_comment корректно парсится."""
        from app.services.llm_service import LLMService

        # Mock LLM response с round комментариями
        mock_llm_response = """{
            "winner": "user",
            "comment": "Пользователь выиграл по очкам",
            "round1_comment": "Раунд 1: Сильное начало, конкретные аргументы",
            "round2_comment": "Раунд 2: Уверенное завершение, согласован результат"
        }"""

        judge_service = JudgeService()

        with patch.object(LLMService, 'is_configured', return_value=True):
            with patch.object(LLMService, 'generate_text', new_callable=AsyncMock) as mock_generate:
                mock_generate.return_value = mock_llm_response

                context = JudgeContext(
                    judge_type="owner",
                    scenario_code="test_scenario",
                    duel_id=1,
                    round1_transcript="Транскрипт раунда 1",
                    round2_transcript="Транскрипт раунда 2",
                )

                verdict = await judge_service.run_single_judge(context)

        assert verdict.winner == "user"
        assert "Пользователь выиграл" in verdict.comment
        assert "Раунд 1" in verdict.round1_comment
        assert "Раунд 2" in verdict.round2_comment

    @pytest.mark.asyncio
    async def test_run_single_judge_handles_missing_round_comments(self, fresh_test_db):
        """Если LLM не вернул round комментарии — используются пустые строки."""
        from app.services.llm_service import LLMService

        # Mock LLM response БЕЗ round комментариев
        mock_llm_response = """{
            "winner": "draw",
            "comment": "Ничья, обе стороны показали равный уровень"
        }"""

        judge_service = JudgeService()

        with patch.object(LLMService, 'is_configured', return_value=True):
            with patch.object(LLMService, 'generate_text', new_callable=AsyncMock) as mock_generate:
                mock_generate.return_value = mock_llm_response

                context = JudgeContext(
                    judge_type="team",
                    scenario_code="test_scenario",
                    duel_id=1,
                    round1_transcript="Транскрипт раунда 1",
                    round2_transcript="Транскрипт раунда 2",
                )

                verdict = await judge_service.run_single_judge(context)

        assert verdict.winner == "draw"
        assert verdict.round1_comment == ""
        assert verdict.round2_comment == ""

    @pytest.mark.asyncio
    async def test_fallback_verdict_has_round_comments(self, fresh_test_db):
        """Fallback verdict всегда содержит round комментарии."""
        judge_service = JudgeService()

        context = JudgeContext(
            judge_type="owner",
            scenario_code="test_scenario",
            duel_id=1,
            round1_transcript="Короткий транскрипт",
            round2_transcript="Короткий транскрипт",
        )

        verdict = judge_service._fallback_verdict(context)

        assert verdict.winner == "draw"
        assert verdict.round1_comment != ""
        assert verdict.round2_comment != ""
        assert "Раунд 1" in verdict.round1_comment
        assert "Раунд 2" in verdict.round2_comment


class TestFormatFinalVerdict:
    """Тесты форматирования финальных итогов."""

    def test_format_verdict_shows_round_breakdown(self):
        """_format_final_verdict отображает разбивку по раундам."""
        from app.bot.handlers.menu import _format_final_verdict

        judge_service = JudgeService()

        verdicts = [
            JudgeVerdict(
                judge_type="owner",
                winner="user",
                comment="Пользователь выиграл",
                round1_comment="Раунд 1: Сильное начало",
                round2_comment="Раунд 2: Уверенное завершение",
            ),
            JudgeVerdict(
                judge_type="team",
                winner="user",
                comment="Команда поддерживает",
                round1_comment="Раунд 1: Ясные позиции",
                round2_comment="Раунд 2: Конструктивный диалог",
            ),
        ]

        final_verdict = "Победа пользователя по мнению большинства судей."

        formatted = _format_final_verdict(judge_service, verdicts, final_verdict)

        # Проверяем наличие общего комментария
        assert "Поединок завершён" in formatted
        assert "Победа пользователя" in formatted

        # Проверяем наличие round breakdown
        assert "Раунд 1: Сильное начало" in formatted
        assert "Раунд 2: Уверенное завершение" in formatted
        assert "Раунд 1: Ясные позиции" in formatted
        assert "Раунд 2: Конструктивный диалог" in formatted

    def test_format_verdict_handles_empty_round_comments(self):
        """_format_final_verdict корректно обрабатывает пустые round комментарии."""
        from app.bot.handlers.menu import _format_final_verdict

        judge_service = JudgeService()

        verdicts = [
            JudgeVerdict(
                judge_type="owner",
                winner="user",
                comment="Пользователь выиграл",
                round1_comment="",  # Пустой
                round2_comment="",  # Пустой
            ),
        ]

        final_verdict = "Победа пользователя"
        formatted = _format_final_verdict(judge_service, verdicts, final_verdict)

        # Общий комментарий есть
        assert "Пользователь выиграл" in formatted

        # Round комментариев нет (они пустые)
        assert "Раунд 1:" not in formatted
        assert "Раунд 2:" not in formatted

    def test_format_verdict_partial_round_comments(self):
        """_format_final_verdict показывает только заполненные round комментарии."""
        from app.bot.handlers.menu import _format_final_verdict

        judge_service = JudgeService()

        verdicts = [
            JudgeVerdict(
                judge_type="owner",
                winner="ai",
                comment="AI выиграл",
                round1_comment="Раунд 1: AI доминировал",
                round2_comment="",  # Пустой
            ),
        ]

        final_verdict = "Победа AI"
        formatted = _format_final_verdict(judge_service, verdicts, final_verdict)

        # Round 1 есть
        assert "Раунд 1: AI доминировал" in formatted

        # Round 2 нет (пустой)
        assert "Раунд 2:" not in formatted


class TestJudgeResultModel:
    """Тесты модели JudgeResult."""

    @pytest.mark.asyncio
    async def test_save_verdict_with_round_comments(self, fresh_test_db):
        """Сохранение вердикта с round комментариями работает корректно."""
        async with db_session.AsyncSessionLocal() as session:
            # Создаём тестовую дуэль с обязательными полями
            duel = Duel(
                status="finished",
                scenario_id=1,
                user_telegram_id=123,
                current_round_number=2,
                user_role_round1="Роль A",
                ai_role_round1="Роль B",
                user_role_round2="Роль B",
                ai_role_round2="Роль A",
            )
            session.add(duel)
            await session.flush()

            # Создаём вердикт с round комментариями
            verdict = JudgeVerdict(
                judge_type="owner",
                winner="user",
                comment="Общий комментарий",
                round1_comment="Комментарий раунда 1",
                round2_comment="Комментарий раунда 2",
            )

            # Сохраняем
            judge_result = await JudgeService().save_verdict(duel, verdict)
            session.add(judge_result)
            await session.commit()

            # Проверяем
            assert judge_result.duel_id == duel.id
            assert judge_result.judge_type == "owner"
            assert judge_result.winner == "user"
            assert judge_result.comment == "Общий комментарий"
            assert judge_result.round1_comment == "Комментарий раунда 1"
            assert judge_result.round2_comment == "Комментарий раунда 2"

    @pytest.mark.asyncio
    async def test_list_judge_results_with_round_comments(self, fresh_test_db):
        """Чтение judge results с round комментариями работает корректно."""
        async with db_session.AsyncSessionLocal() as session:
            # Создаём дуэль с обязательными полями
            duel = Duel(
                status="finished",
                scenario_id=1,
                user_telegram_id=123,
                user_role_round1="Роль A",
                ai_role_round1="Роль B",
                user_role_round2="Роль B",
                ai_role_round2="Роль A",
            )
            session.add(duel)
            await session.flush()

            # Создаём judge result с round комментариями
            judge_result = JudgeResult(
                duel_id=duel.id,
                judge_type="team",
                winner="draw",
                comment="Ничья",
                round1_comment="Раунд 1: Равная игра",
                round2_comment="Раунд 2: Компромисс",
            )
            session.add(judge_result)
            await session.commit()

            # Читаем
            results = await DuelService().list_judge_results(session, duel.id)

            assert len(results) == 1
            assert results[0].round1_comment == "Раунд 1: Равная игра"
            assert results[0].round2_comment == "Раунд 2: Компромисс"


class TestIntegration:
    """Интеграционные тесты полного цикла."""

    @pytest.mark.asyncio
    async def test_full_judge_flow_with_round_breakdown(self, fresh_test_db):
        """Полный цикл: LLM → save → format → round breakdown отображается."""
        from app.services.llm_service import LLMService
        from app.bot.handlers.menu import _format_final_verdict

        async with db_session.AsyncSessionLocal() as session:
            # Создаём дуэль с обязательными полями
            duel = Duel(
                status="round_2_transition",
                scenario_id=1,
                user_telegram_id=123,
                user_role_round1="Роль A",
                ai_role_round1="Роль B",
                user_role_round2="Роль B",
                ai_role_round2="Роль A",
            )
            session.add(duel)
            await session.flush()

            # Mock LLM responses для всех трёх судей
            mock_responses = [
                '{"winner": "user", "comment": "Owner: пользователь выиграл", "round1_comment": "R1: сильно", "round2_comment": "R2: уверенно"}',
                '{"winner": "user", "comment": "Team: пользователь лучше", "round1_comment": "R1: ясно", "round2_comment": "R2: конструктивно"}',
                '{"winner": "draw", "comment": "Sender: ничья", "round1_comment": "R1: равно", "round2_comment": "R2: компромисс"}',
            ]

            judge_service = JudgeService()

            with patch.object(LLMService, 'is_configured', return_value=True):
                with patch.object(LLMService, 'generate_text', new_callable=AsyncMock) as mock_generate:
                    mock_generate.side_effect = mock_responses

                    # Запускаем всех судей
                    contexts = judge_service.build_contexts_for_duel(
                        duel=duel,
                        scenario_code="test",
                        round1_messages=[],
                        round2_messages=[],
                    )
                    verdicts = await judge_service.run_all_judges(contexts)

                    # Сохраняем вердикты
                    for verdict in verdicts:
                        jr = await judge_service.save_verdict(duel, verdict)
                        session.add(jr)
                    await session.commit()

            # Форматируем итоги
            final_verdict = judge_service.summarize_final_verdict(verdicts)
            formatted = _format_final_verdict(judge_service, verdicts, final_verdict)

            # Проверяем что round breakdown отображается
            assert "R1: сильно" in formatted or "Раунд 1" in formatted
            assert "R2: уверенно" in formatted or "Раунд 2" in formatted

            # Проверяем что все 3 судьи есть
            assert "Owner" in formatted or "собственник" in formatted
            assert "Team" in formatted or "команда" in formatted
            assert "Sender" in formatted or "отправляющий" in formatted
