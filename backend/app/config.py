# app/config.py
# Reads every setting from environment variables (or the .env file).
# Secrets never live in code: change a value in .env, not here.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Tell pydantic-settings to also read a .env file in the backend folder
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database ---
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/adaptlearn"

    # --- Auth (JWT) ---
    secret_key: str = "change-me-in-production"   # used to sign tokens
    access_token_expire_minutes: int = 60 * 24     # token valid for 24 hours

    # --- Frontend allowed to call this API (comma-separated list) ---
    cors_origins: str = "http://localhost:5173"

    # --- Optional services: the app still works if these are empty ---
    redis_url: str | None = None
    openai_api_key: str | None = None
    # Pick a current cheap model from OpenAI's models page and put it in .env
    openai_model: str = "gpt-6-luna"
    # "low" keeps reasoning models fast and cheap. Leave it empty in .env if your
    # model is not a reasoning model (the API would reject the parameter).
    openai_reasoning_effort: str = "low"
    cache_ttl_seconds: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        """'a,b' -> ['a', 'b']"""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# One shared settings object, imported everywhere
settings = Settings()
