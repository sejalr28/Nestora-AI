"""
Centralized app configuration.

Why this file exists: every other module (database, LLM provider, Twilio
client) should import `settings` from here instead of reading os.environ
directly. That keeps config in one auditable place and makes testing easy
(you can override `settings` in tests without touching env vars).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    database_url: str = "postgresql://societyboard:societyboard@localhost:5432/societyboard"

    # --- App ---
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5174"

    # --- LLM provider selection (see services/llm/) ---
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None

    # --- Twilio WhatsApp ---
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_whatsapp_number: str = "whatsapp:+14155238886"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Single shared instance — import this, don't instantiate Settings() elsewhere.
settings = Settings()
