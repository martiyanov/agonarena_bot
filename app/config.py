from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8080
    app_base_url: str = "http://localhost:8080"

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    telegram_bot_username: str = ""

    database_url: str = "sqlite+aiosqlite:///./data/agonarena.db"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4.1-mini"
    stt_model: str = "whisper-1"

    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()


def get_database_url_for_env() -> str:
    """Выбираем БД в зависимости от окружения.

    Для локальной разработки используем отдельную dev-базу,
    чтобы не трогать боевую и не упираться в read-only.
    """
    env = settings.app_env.lower()
    if env in {"dev", "development_local", "local"}:
        return "sqlite+aiosqlite:///./data/agonarena_dev.db"
    return settings.database_url
