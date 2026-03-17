"""
enrichment/memory.py
────────────────────
Loads and saves the query-weight memory file.
The memory dict maps query_id (int) → hit_count (int).
Higher counts = that query pattern worked well → gets sorted first.
"""

import json
import logging
from enrichment import config

logger = logging.getLogger(__name__)

_DEFAULT_MEMORY: dict[int, int] = {i: 0 for i in range(10)}


def load_memory() -> dict[int, int]:
    """
    Load memory from disk.
    Returns a fresh default dict if the file is missing or corrupted.
    """
    if not config.MEMORY_FILE.exists():
        logger.info("No memory file found — starting fresh.")
        return dict(_DEFAULT_MEMORY)

    try:
        with open(config.MEMORY_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        memory = {int(k): int(v) for k, v in raw.items()}
        logger.info(f"Memory loaded ({len(memory)} query weights) from {config.MEMORY_FILE}")
        return memory
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning(f"Memory file corrupted ({e}) — resetting to defaults.")
        return dict(_DEFAULT_MEMORY)


def save_memory(memory: dict[int, int]) -> None:
    """Persist memory to disk. Fails gracefully — a save error never crashes the run."""
    try:
        with open(config.MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=2)
        logger.debug("Memory saved.")
    except IOError as e:
        logger.error(f"Could not save memory file: {e}")
