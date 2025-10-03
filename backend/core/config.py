from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(protected_namespaces=("settings_",))
    # Retrieval
    retrieval_k: int = 50  # can be overridden per-request by payload "topk"

    # LLM usage (OFF by default)
    use_llm_overview: bool = True # if True, overview text is phrased via Ollama

    # LLM routing (Ollama only)
    llm_primary: str = "ollama"        # fixed
    llm_timeout_s: int = 20
    ollama_url: str = "http://127.0.0.1:11434/api/generate"
    ollama_model: str = "qwen2.5:7b"   # or "llama3.1:8b", etc.
    # Attempt to auto-pull the configured model on startup if missing
    auto_pull_model: bool = True

    # Ollama generation defaults (tunable)
    # Lower temperature and modest top_p keep outputs concise and factual.
    ollama_temperature: float = 0.2
    ollama_top_p: float = 0.9
    ollama_num_predict: int = 256
    ollama_num_ctx: int = 4096
    ollama_repeat_penalty: float = 1.1
    # System guidance to improve executive tone and structure
    ollama_system: str = (
        "You are a senior security analyst writing executive briefs for leadership. "
        "Be concise, precise, and action-oriented. Avoid speculation, avoid marketing language, "
        "and do not use markdown, emojis, or headings. Keep critical figures and names intact."
    )

    # API config fields used by /config
    model_backend: str = "ollama"
    model_name: str = "qwen2.5:7b"
    language: str = "en"
    enable_validation: bool = False

    # App meta
    version: str = "censai-summarizer-0.4"


settings = Settings()