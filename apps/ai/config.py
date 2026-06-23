from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """
    Application settings.
    """

    openai_api_key: str

    openai_model: str = "gpt-4.1"

    temperature: float = 0.0

    max_tokens: int = 4000

    app_name: str = "AI Recruitment"

    app_version: str = "1.0.0"

    debug: bool = True

    output_folder: str = "outputs"

    temp_folder: str = "temp"

    log_folder: str = "logs"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return application settings.
    """

    return Settings()
