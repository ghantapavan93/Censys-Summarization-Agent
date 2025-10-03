import subprocess
import shutil


def has_ollama() -> bool:
    return shutil.which("ollama") is not None


def run_ollama(prompt: str, model: str = "qwen2.5:7b", timeout_sec: int = 120) -> str:
    if not has_ollama():
        raise FileNotFoundError("Ollama not found. Install from https://ollama.ai and ensure it's on PATH.")
    p = subprocess.run(
        ["ollama", "run", model],
        input=prompt.encode("utf-8"),
        capture_output=True,
        timeout=timeout_sec
    )
    if p.returncode != 0:
        err = (p.stderr or b"").decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"Ollama failed for model '{model}'. Tip: run 'ollama pull {model}'. Details: {err.strip()}"
        )
    return p.stdout.decode("utf-8", errors="ignore").strip()
from ..core.config import settings


class LLMRouter:
    """Minimal Ollama-only router with sane defaults and overrides."""

    def __init__(self) -> None:
        if settings.llm_primary != "ollama":
            raise RuntimeError("LLM is locked to Ollama. Set llm_primary='ollama'.")
        self.timeout_s = settings.llm_timeout_s

    def _ollama_complete(self, prompt: str, *, model: str | None = None, system: str | None = None) -> str:
        import requests
        url = settings.ollama_url
        mdl = model or settings.ollama_model
        opts = {
            "temperature": settings.ollama_temperature,
            "top_p": settings.ollama_top_p,
            "repeat_penalty": settings.ollama_repeat_penalty,
            "num_ctx": settings.ollama_num_ctx,
            "num_predict": settings.ollama_num_predict,
        }
        payload = {
            "model": mdl,
            "prompt": prompt,
            "system": system or settings.ollama_system,
            "stream": False,
            "options": opts,
        }
        r = requests.post(url, json=payload, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        return (data.get("response") or data.get("output") or "").strip()

    def complete(self, prompt: str, *, model: str | None = None, system: str | None = None) -> str:
        return self._ollama_complete(prompt, model=model, system=system)