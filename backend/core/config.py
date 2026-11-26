import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


# Load .env from repo root or backend/ without overwriting shell variables.
_BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(_BACKEND_DIR.parent / ".env")
load_dotenv(_BACKEND_DIR / ".env")


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    # LLM selection: "auto" uses Azure OpenAI when endpoint + key are set, else Ollama.
    llm_provider: str = os.getenv("LLM_PROVIDER", "auto").strip().lower()
    llm_timeout_seconds: int = _int("LLM_TIMEOUT_SECONDS", 120)

    # Azure OpenAI settings
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    azure_openai_deployment: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini").strip()
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview").strip()
    azure_max_tokens: int = _int("AZURE_MAX_TOKENS", 8192)

    # Local Ollama fallback settings (tuned for 8 GB VRAM)
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    ollama_context_size: int = _int("OLLAMA_CONTEXT_SIZE", 32768)
    ollama_max_tokens: int = _int("OLLAMA_MAX_TOKENS", 8192)

    log_dir: str = os.getenv("LOG_DIR", str(_BACKEND_DIR / "logs"))

    # Optional Langfuse observability settings (Cloud or self-hosted Docker).
    langfuse_public_key: str = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    langfuse_secret_key: str = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    langfuse_base_url: str = (
        os.getenv("LANGFUSE_BASE_URL")
        or os.getenv("LANGFUSE_HOST")
        or "https://cloud.langfuse.com"
    ).strip()
    langfuse_environment: str = os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "local").strip()

    search_timeout_seconds: int = _int("SEARCH_TIMEOUT_SECONDS", 45)
    http_timeout_seconds: int = _int("HTTP_TIMEOUT_SECONDS", 20)
    http_max_retries: int = _int("HTTP_MAX_RETRIES", 2)
    max_search_results: int = _int("MAX_SEARCH_RESULTS", 5)
    max_evidence_results: int = _int("MAX_EVIDENCE_RESULTS", 15)
    validation_batch_size: int = _int("VALIDATION_BATCH_SIZE", 5)
    max_research_rounds: int = _int("MAX_RESEARCH_ROUNDS", 2)
    max_total_sources: int = _int("MAX_TOTAL_SOURCES", 15)
    pages_per_query: int = _int("PAGES_PER_QUERY", 5)
    page_fetch_timeout_seconds: int = _int("PAGE_FETCH_TIMEOUT_SECONDS", 8)
    max_page_chars: int = _int("MAX_PAGE_CHARS", 12000)
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    cors_origins: list[str] = field(default_factory=lambda: [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
        ).split(",")
        if origin.strip()
    ])


settings = Settings()
