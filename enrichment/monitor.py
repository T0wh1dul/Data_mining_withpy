"""
enrichment/monitor.py
─────────────────────
Lightweight run-event and search-history logging for dashboard monitoring.
"""

import json
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict

from enrichment import config

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    """Append one JSON object per line. Never crash caller on logging failure."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except Exception as exc:
        logger.debug(f"Monitor append failed for {path}: {exc}")


def log_event(event_type: str, level: str = "info", **data: Any) -> None:
    payload: Dict[str, Any] = {
        "ts": _now_iso(),
        "type": event_type,
        "level": level,
        **data,
    }
    _append_jsonl(config.EVENTS_FILE, payload)


def log_search_event(
    query: str,
    max_results: int,
    status: str,
    provider: str,
    result_count: int = 0,
    error: str = "",
) -> None:
    payload: Dict[str, Any] = {
        "ts": _now_iso(),
        "query": query,
        "max_results": max_results,
        "status": status,
        "provider": provider,
        "result_count": result_count,
    }
    if error:
        payload["error"] = error[:250]
    _append_jsonl(config.SEARCH_HISTORY_FILE, payload)
