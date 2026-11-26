import contextvars
import json
import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config import settings


logger = logging.getLogger(__name__)


@dataclass
class RunTrace:
    """Captures all logs and provenance details for one research request."""

    run_id: str
    path: Path
    started_at: float = field(default_factory=time.perf_counter)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def write(self, text: str) -> None:
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(text)
                if not text.endswith("\n"):
                    fh.write("\n")

    def section(self, title: str, body: str) -> None:
        bar = "=" * 72
        self.write(f"\n{bar}\n[{title}]\n{bar}\n{body.rstrip()}\n")


_current_run: contextvars.ContextVar[RunTrace | None] = contextvars.ContextVar(
    "current_research_run",
    default=None,
)


class _RunContextLogHandler(logging.Handler):
    """Mirror Python logging records into the active request's .log file."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s", "%H:%M:%S")
        )

    def emit(self, record: logging.LogRecord) -> None:
        trace = _current_run.get()
        if trace is None:
            return
        try:
            trace.write(self.format(record))
        except Exception:
            pass


_handler_installed = False


def install_run_logging() -> None:
    """Attach the per-run context handler to the root logger once."""
    global _handler_installed
    if _handler_installed:
        return
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(_RunContextLogHandler())
    _handler_installed = True


def _slug(text: str, max_len: int = 40) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (cleaned[:max_len].strip("-") or "research")


def start_run_log(query: str, *, mode: str, plan: dict | None = None, use_memory: bool = False) -> tuple[RunTrace, contextvars.Token]:
    """Create a new per-run .log file in `settings.log_dir` and bind it to the async context."""
    install_run_logging()
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = uuid.uuid4().hex[:8]
    path = log_dir / f"{stamp}_{_slug(query)}_{run_id}.log"

    trace = RunTrace(run_id=run_id, path=path)
    header = [
        f"Run ID    : {run_id}",
        f"Endpoint  : {mode}",
        f"Timestamp : {datetime.now().isoformat(timespec='seconds')}",
        f"Query     : {query}",
        f"Use Memory: {use_memory}",
    ]
    if plan:
        header.append(f"Approved Plan:\n{json.dumps(plan, indent=2)}")
    trace.section("RUN START", "\n".join(header))

    token = _current_run.set(trace)
    logger.info("Research run %s started -> log file: %s", run_id, path)
    return trace, token


def log_section(title: str, body: str) -> None:
    """Append a structured provenance block to the active run's log file."""
    trace = _current_run.get()
    if trace is not None:
        trace.section(title, body)


def finish_run_log(
    trace: RunTrace,
    token: contextvars.Token,
    *,
    status: str,
    sources_count: int = 0,
    error: str = "",
) -> None:
    elapsed = time.perf_counter() - trace.started_at
    lines = [
        f"Status        : {status}",
        f"Elapsed       : {elapsed:.2f}s",
        f"Sources Kept  : {sources_count}",
    ]
    if error:
        lines.append(f"Error         : {error}")
    trace.section("RUN END", "\n".join(lines))
    logger.info("Research run %s finished (%s in %.2fs) -> %s", trace.run_id, status, elapsed, trace.path)
    _current_run.reset(token)


def format_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, default=str)
