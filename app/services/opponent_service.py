from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, ConfigDict

from app.db.models import DuelMessage
from app.services.llm_service import LLMService

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "opponent.md"


class OpponentTurnContext(BaseModel):
    """Контекст для генерации ответа AI-оппонента.

    Здесь только примитивы, без прямых ссылок на ORM-модели, чтобы не плодить
    pydantic-схемы для SQLAlchemy-типов.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    scenario_title: str = ""
    scenario_description: str = ""
    round_number: int
    user_role: str
    ai_role: str
    opening_line: str
    history: Sequence[DuelMessage]


class OpponentService:
    """AI-оппонент с LLM-first режимом и fallback на rule-based ответ."""

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()
        self.system_prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    async def generate_reply(self, context: OpponentTurnContext) -> str:
        if self.llm_service.is_configured():
            try:
                return await self.llm_service.generate_text(
                    system_prompt=self.system_prompt,
                    user_prompt=self._build_user_prompt(context),
                    temperature=0.8,
                )
            except Exception:
                # На любых ошибках LLM не роняем поединок, а уходим в fallback.
                pass

        return self._fallback_reply(context)

    def _build_user_prompt(self, context: OpponentTurnContext) -> str:
        transcript = self._transcript(context.history)
        return (
            f"Scenario: {context.scenario_title}\n"
            f"Description: {context.scenario_description}\n"
            f"Round: {context.round_number}\n"
            f"User role: {context.user_role}\n"
            f"AI role: {context.ai_role}\n"
            f"Opening line: {context.opening_line}\n"
            f"Transcript:\n{transcript}\n\n"
            "Generate the next AI reply in character. Reply in Russian."
        )

    def _transcript(self, history: Sequence[DuelMessage]) -> str:
        if not history:
            return "(empty)"
        lines: list[str] = []
        for msg in history:
            prefix = "user" if msg.author == "user" else "ai"
            lines.append(f"{prefix}: {msg.content}")
        return "\n".join(lines)

    def _fallback_reply(self, context: OpponentTurnContext) -> str:
        last_user_message = next((m for m in reversed(context.history) if m.author == "user"), None)
        user_text = last_user_message.content if last_user_message else ""

        ai_role = context.ai_role
        user_role = context.user_role
        base_intro = f"[{ai_role}] отвечает [{user_role}]:"

        if not user_text:
            return f"{base_intro} начнём с того, что вы подробнее опишете свою позицию?"

        return (
            f"{base_intro} я услышал вашу позицию — \"{user_text}\". "
            "Сформулируйте, на какие условия вы готовы пойти, и я скажу, что могу принять со своей стороны."
        )
