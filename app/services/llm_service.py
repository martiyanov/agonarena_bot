import httpx

from app.config import settings


class LLMService:
    """Минимальный OpenAI-compatible клиент для MVP.

    Если ключ не задан, вызывающая сторона может использовать fallback-логику.
    """

    def is_configured(self) -> bool:
        return bool(settings.openai_api_key)

    async def generate_text(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        if not self.is_configured():
            raise RuntimeError("LLM is not configured")

        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{settings.openai_base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]["content"].strip()
