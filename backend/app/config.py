"""
Application configuration with Pydantic Settings.

All settings can be configured via environment variables with FITNESS_ prefix.
API keys use SecretStr to prevent accidental logging.
"""
import threading
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment variables use FITNESS_ prefix:
    - FITNESS_AI_PROVIDER=anthropic
    - FITNESS_ANTHROPIC_API_KEY=sk-ant-...

    Use .env file for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FITNESS_",
        extra="ignore",
        case_sensitive=False,
    )

    # === Provider Selection ===
    ai_provider: Literal["anthropic", "openai", "ollama"] = "anthropic"
    embedding_provider: Literal["openai", "ollama", "none"] = "openai"
    rag_provider: Literal["pgvector", "sqlite", "none"] = "pgvector"
    graph_provider: Literal["networkx", "neo4j", "none"] = "networkx"

    # === Anthropic ===
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"

    # === OpenAI ===
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # === Ollama ===
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"

    # === Database ===
    database_url: str = "postgresql+asyncpg://fitness:fitness@localhost/fitness"

    # === RAG ===
    rag_collection: str = "fitness_memory"
    embedding_dimensions: int = 1536
    sqlite_vec_path: str = "./data/vectors.db"

    # === Graph ===
    graph_storage_path: str = "./data/fitness_graph.json"
    neo4j_uri: str | None = None
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr | None = None

    # === Application ===
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

    # === Rate Limiting ===
    rate_limit_chat: str = "10/minute"
    rate_limit_default: str = "100/minute"

    @model_validator(mode="after")
    def validate_provider_keys(self) -> "Settings":
        """Validate that required API keys are set for selected providers."""
        # AI Provider validation
        if self.ai_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "FITNESS_ANTHROPIC_API_KEY required when ai_provider=anthropic"
            )
        if self.ai_provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "FITNESS_OPENAI_API_KEY required when ai_provider=openai"
            )

        # Embedding Provider validation
        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "FITNESS_OPENAI_API_KEY required when embedding_provider=openai"
            )

        return self


# Thread-safe singleton
_settings: Settings | None = None
_settings_lock = threading.Lock()


def get_settings() -> Settings:
    """
    Get application settings (thread-safe singleton).

    Settings are loaded once and cached for the application lifetime.
    """
    global _settings

    if _settings is None:
        with _settings_lock:
            if _settings is None:
                _settings = Settings()

    return _settings


def reset_settings() -> None:
    """Reset settings singleton. Used for testing."""
    global _settings
    _settings = None
