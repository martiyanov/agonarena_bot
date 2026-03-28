import httpx
import logging

from app.config import settings


logger = logging.getLogger(__name__)


class LLMService:
    """LLM клиент с fallback логикой.

    Priority:
    1. ModelStudio (qwen3.5-plus, qwen3-coder-plus) — primary
    2. OpenAI (gpt-4o-mini) — fallback, только если ModelStudio недоступен
    
    OpenAI используется только в крайних случаях с предварительным уведомлением.
    """

    PRIMARY_MODELS = [
        "qwen3.5-plus",
        "qwen3-coder-plus",
        "qwen3-max-2026-01-23",
    ]
    
    FALLBACK_MODELS = [
        "gpt-4o-mini",
        "gpt-4.1-mini",
    ]

    def is_configured(self) -> bool:
        """Проверяет доступен ли хотя бы один LLM provider."""
        return bool(settings.modelstudio_api_key) or bool(settings.openai_api_key)

    def is_primary_configured(self) -> bool:
        """Проверяет доступен ли primary provider (ModelStudio)."""
        return bool(settings.modelstudio_api_key)

    def is_fallback_configured(self) -> bool:
        """Проверяет доступен ли fallback provider (OpenAI)."""
        return bool(settings.openai_api_key)

    async def generate_text(
        self, 
        *, 
        system_prompt: str, 
        user_prompt: str, 
        temperature: float = 0.7,
        use_fallback: bool = False
    ) -> str:
        """
        Генерирует текст с fallback логикой.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            temperature: Temperature (0.0-2.0)
            use_fallback: Если True — сразу использовать fallback (OpenAI)
        
        Returns:
            Generated text
        
        Raises:
            RuntimeError: Если ни один provider не доступен
            httpx.HTTPError: Если все providers не доступны
        """
        # Определяем какой provider использовать
        if use_fallback or not self.is_primary_configured():
            if self.is_fallback_configured():
                logger.warning("Using FALLBACK LLM provider (OpenAI) — primary (ModelStudio) unavailable")
                return await self._generate_with_provider(
                    provider="openai",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                )
            else:
                raise RuntimeError(
                    "LLM fallback not configured. "
                    "ModelStudio API key not set AND OpenAI API key not set. "
                    "Add MODELSTUDIO_API_KEY or OPENAI_API_KEY to .env"
                )
        
        # Пробуем primary (ModelStudio)
        try:
            return await self._generate_with_provider(
                provider="modelstudio",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )
        except Exception as e:
            logger.error("Primary LLM (ModelStudio) failed: %s", e)
            
            # Fallback на OpenAI если доступен
            if self.is_fallback_configured():
                logger.warning("Falling back to OpenAI after ModelStudio failure")
                try:
                    return await self._generate_with_provider(
                        provider="openai",
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=temperature,
                    )
                except Exception as fallback_error:
                    logger.error("Fallback LLM (OpenAI) also failed: %s", fallback_error)
                    raise RuntimeError(f"Both LLM providers failed. Last error: {fallback_error}")
            
            # Если fallback недоступен — пробрасываем ошибку primary
            raise

    async def _generate_with_provider(
        self,
        *,
        provider: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> str:
        """Генерирует текст с указанным provider."""
        if provider == "modelstudio":
            api_key = settings.modelstudio_api_key
            base_url = settings.modelstudio_base_url
            model = settings.llm_model
        elif provider == "openai":
            api_key = settings.openai_api_key
            base_url = settings.openai_base_url
            model = settings.openai_fallback_model
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]["content"].strip()
