import asyncio
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from core.config import settings


logger = logging.getLogger(__name__)

_client: Any = None
_client_checked = False


def langfuse_enabled() -> bool:
    return bool(settings.langfuse_public_key and settings.langfuse_secret_key)


def _get_langfuse_client() -> Any:
    """Lazily initialize the Langfuse singleton once when credentials are configured."""
    global _client, _client_checked
    if _client_checked:
        return _client
    _client_checked = True

    if not langfuse_enabled():
        return None

    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            base_url=settings.langfuse_base_url,
            environment=settings.langfuse_environment,
        )
        logger.info("Langfuse observability enabled (host=%s)", settings.langfuse_base_url)
    except Exception:
        logger.exception("Failed to initialize Langfuse client; tracing disabled")
        _client = None

    return _client


def flush_langfuse() -> None:
    if _client is not None:
        try:
            _client.flush()
        except Exception:
            logger.warning("Langfuse flush failed", exc_info=True)


async def aflush_langfuse() -> None:
    if _client is not None:
        await asyncio.to_thread(flush_langfuse)


@contextmanager
def langfuse_trace(
    trace_name: str,
    *,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield a LangChain/LangGraph runnable config with Langfuse tracing attached.

    Returns `{}` when Langfuse credentials are not configured, keeping runs unaffected.
    """
    client = _get_langfuse_client()
    if client is None:
        yield {}
        return

    try:
        from langfuse import propagate_attributes
        from langfuse.langchain import CallbackHandler

        handler = CallbackHandler(public_key=settings.langfuse_public_key)
        clean_meta = {
            k: str(v)[:200]
            for k, v in (metadata or {}).items()
            if v is not None
        }
        with propagate_attributes(
            trace_name=trace_name,
            session_id=session_id,
            metadata=clean_meta or None,
            tags=tags,
        ):
            yield {"callbacks": [handler], "run_name": trace_name}
    except Exception:
        logger.warning("Langfuse trace setup failed; continuing without tracing", exc_info=True)
        yield {}
