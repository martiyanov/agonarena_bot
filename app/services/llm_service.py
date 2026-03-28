import httpx
import logging

from app.config import settings


logger = logging.getLogger(__name__)


class LLMService:
    """LLM клиент с fallback логикой.

    Priority:
    1. ModelStudio (qwen3.5-plus, qwen3-coder-plus) — PRIMARY
    2. Kimi (kimi-k2.5) — FALLBACK 1
    3. OpenAI (gpt-4o-mini) — FALLBACK 2 (last resort)
    
    OpenAI используется только в крайних случаях.
    """

    PRIMARY_MODELS = [
        "qwen3.5-plus",
        "qwen3-coder-plus",
        "qwen3-max-2026-01-23",
    ]
    
    FALLBACK_1_MODELS = [
        "kimi-k2.5",
        "kimi-code",
    ]
    
    FALLBACK_2_MODELS = [
        "gpt-4o-mini",
        "gpt-4.1-mini",
    ]

    def is_configured(self) -> bool:
        """Проверяет доступен ли хотя бы один LLM provider."""
        return (
            bool(settings.modelstudio_api_key) or 
            bool(settings.kimi_api_key) or 
            bool(settings.openai_api_key)
        )

    def is_primary_configured(self) -> bool:
        """Проверяет доступен ли primary provider (ModelStudio)."""
        return bool(settings.modelstudio_api_key)

    def is_fallback1_configured(self) -> bool:
        """Проверяет доступен ли fallback 1 (Kimi)."""
        return bool(settings.kimi_api_key)

    def is_fallback2_configured(self) -> bool:
        """Проверяет доступен ли fallback 2 (OpenAI)."""
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
        
        Priority: ModelStudio → Kimi → OpenAI
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            temperature: Temperature (0.0-2.0)
            use_fallback: Если True — сразу использовать fallback 1 (Kimi)
        
        Returns:
            Generated text
        
        Raises:
            RuntimeError: Если ни один provider не доступен
            httpx.HTTPError: Если все providers не доступны
        """
        # Определяем какой provider использовать
        if use_fallback or not self.is_primary_configured():
            return await self._try_fallback_chain(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
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
            return await self._try_fallback_chain(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                primary_error=e,
            )

    async def _try_fallback_chain(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        primary_error: Exception = None,
    ) -> str:
        """Пытается выполнить запрос через цепочку fallback providers."""
        # Fallback 1: Kimi
        if self.is_fallback1_configured():
            try:
                logger.warning("Using FALLBACK 1 LLM provider (Kimi) — ModelStudio unavailable")
                return await self._generate_with_provider(
                    provider="kimi",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                )
            except Exception as e1:
                logger.error("Fallback 1 LLM (Kimi) failed: %s", e1)
        
        # Fallback 2: OpenAI
        if self.is_fallback2_configured():
            try:
                logger.warning("Using FALLBACK 2 LLM provider (OpenAI) — ModelStudio + Kimi unavailable")
                return await self._generate_with_provider(
                    provider="openai",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                )
            except Exception as e2:
                logger.error("Fallback 2 LLM (OpenAI) also failed: %s", e2)
                raise RuntimeError(
                    f"All LLM providers failed. "
                    f"ModelStudio: {primary_error}, Kimi: {e1}, OpenAI: {e2}"
                )
        
        # Если ни один fallback не доступен
        raise RuntimeError(
            "No LLM providers configured. "
            "Add MODELSTUDIO_API_KEY (primary), KIMI_API_KEY (fallback 1), "
            "or OPENAI_API_KEY (fallback 2) to .env"
        )

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
        elif provider == "kimi":
            api_key = settings.kimi_api_key
            base_url = settings.kimi_base_url
            model = settings.kimi_fallback_model
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
