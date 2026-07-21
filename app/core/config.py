from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_env: str = "local"
    app_debug: bool = True

    # Database
    db_host: str
    db_port: int = 3306
    db_database: str
    db_username: str
    db_password: str = ""

    # JWT
    jwt_secret: str
    jwt_algo: str = "HS256"

    # CORS
    allowed_origins: str = ""

    @property
    def database_url(self) -> str:
        """
        SQLAlchemy connection string, built from individual DB_* values.
        Uses asyncmy as the async MySQL driver.
        """
        return (
            f"mysql+asyncmy://{self.db_username}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_database}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        """Converts comma-separated ALLOWED_ORIGINS string into a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Without caching, every import would re-read and re-parse the .env file —
    wasteful since these values never change during runtime.
    """
    return Settings()