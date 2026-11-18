import os
from dataclasses import dataclass, field


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    # 32K context (~1.8 GB KV cache) + ~4.7 GB Q4 weights = ~6.5 GB total, fitting in 8 GB VRAM.
    ollama_context_size: int = _int("OLLAMA_CONTEXT_SIZE", 32768)
    ollama_max_tokens: int = _int("OLLAMA_MAX_TOKENS", 8192)
    search_timeout_seconds: int = _int("SEARCH_TIMEOUT_SECONDS", 45)
    http_timeout_seconds: int = _int("HTTP_TIMEOUT_SECONDS", 20)
    http_max_retries: int = _int("HTTP_MAX_RETRIES", 2)
    max_search_results: int = _int("MAX_SEARCH_RESULTS", 5)
    max_evidence_results: int = _int("MAX_EVIDENCE_RESULTS", 15)
    validation_batch_size: int = _int("VALIDATION_BATCH_SIZE", 5)
    max_research_rounds: int = _int("MAX_RESEARCH_ROUNDS", 2)
    max_total_sources: int = _int("MAX_TOTAL_SOURCES", 15)
    pages_per_query: int = _int("PAGES_PER_QUERY", 3)
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
