from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    database_url: str = (
        "postgresql+asyncpg://decisioncourt:decisioncourt@localhost:5432/decisioncourt"
    )

    model_debate: str = "llama-3.3-70b-versatile"
    model_verdict: str = "openai/gpt-oss-120b"
    model_dev: str = "llama-3.1-8b-instant"
    dev_mode: bool = False

    max_tokens_per_turn: int = 900
    max_tokens_per_session: int = 40000
    max_judge_questions: int = 5

    # Rate limit on session creation, per client IP.
    rate_limit_sessions: int = 20
    rate_limit_window_sec: int = 3600

    cors_origins: str = "http://localhost:5173"
    crisis_region: str = "US"

    def debate_model(self) -> str:
        return self.model_dev if self.dev_mode else self.model_debate

    def verdict_model(self) -> str:
        return self.model_dev if self.dev_mode else self.model_verdict

    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
