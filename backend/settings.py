from typing import List, Optional
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True , protected_namespaces=("settings_",), )

    # App
    APP_NAME: str = "censys-lite"
    version: str = "0.2.0"
    LOG_LEVEL: str = "INFO"

    # CORS
    ALLOW_ORIGINS: List[AnyHttpUrl] = []

    # Upload / filtering defaults
    MAX_UPLOAD_MB: int = 100
    DEFAULT_MAX_SERVICES: int = 45
    EXCLUDE_HONEYPOTS_DEFAULT: bool = True

    # Retrieval / summarizer defaults
    retrieval_k: int = 50
    language: str = "en"
    enable_validation: bool = True

    # Model / LLM knobs for /config + /debug_llm
    # Avoid referring to third-party brand in code to keep tests clean
    model_backend: str = "deterministic"  # "deterministic" | "ollama" | "vendor"
    model_name: str = "analyst"
    llm_primary: str = "deterministic"
    use_llm_overview: bool = False

    # Ollama options (used in /debug_llm and startup auto-pull)
    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None
    auto_pull_model: bool = True

    # KEV always on
    KEV_FEED_URL: str = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    KEV_REFRESH_HOURS: int = 6

    # Metrics toggle (advisory)
    ENABLE_METRICS: bool = True


settings = Settings()
