"""
enrichment/search.py
────────────────────
Low-level DuckDuckGo search wrapper.

Improvements vs original:
  • Exponential backoff on transient failures (2s → 4s → 8s)
  • RateLimitException is raised immediately without retrying
    (caller decides whether to sleep/abort)
  • Connectivity probe only fires when results are empty
  • All retry decisions are centralised here, not scattered in callers
"""

import time
import logging
from typing import List, Dict

from ddgs import DDGS

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
MAX_RETRIES    = 3
RETRY_BACKOFF  = [2, 4, 8]   # seconds between attempts (exponential)
RATE_SIGNALS   = ("ratelimit", "202", "blocked", "too many requests")


class RateLimitException(Exception):
    """Raised when DuckDuckGo returns a rate-limit / IP-block response."""


# ── Public API ───────────────────────────────────────────────────────────────

def get_search_results(query: str, max_res: int = 10) -> List[Dict]:
    """
    Execute a DuckDuckGo text search with automatic retries.

    Returns a (possibly empty) list of result dicts on success.
    Raises RateLimitException if DuckDuckGo blocks the request.
    """
    for attempt in range(MAX_RETRIES):
        try:
            results = _fetch(query, max_res)
            return results
        except RateLimitException:
            raise   # Never retry a rate-limit — propagate immediately
        except Exception as exc:
            wait = RETRY_BACKOFF[attempt]
            logger.warning(
                f"Search attempt {attempt + 1}/{MAX_RETRIES} failed "
                f"({exc.__class__.__name__}: {exc}) — retrying in {wait}s"
            )
            time.sleep(wait)

    logger.error(f"All {MAX_RETRIES} attempts failed for query: {query!r}")
    return []


# ── Private Helpers ──────────────────────────────────────────────────────────

def _fetch(query: str, max_res: int) -> List[Dict]:
    """Single DDGS call. Raises RateLimitException or re-raises other errors."""
    with DDGS() as ddgs:
        try:
            results = list(ddgs.text(query, max_results=max_res))
        except Exception as exc:
            _check_rate_limit(exc)
            raise  # Not a rate-limit — let the retry loop handle it

        if not results:
            # Empty result could mean rate-limited; probe with a neutral query
            probe = list(ddgs.text("technology", max_results=1))
            if not probe:
                raise RateLimitException("Empty response on probe — likely rate limited.")

        return results


def _check_rate_limit(exc: Exception) -> None:
    """Raise RateLimitException if the exception looks like a block."""
    msg = str(exc).lower()
    if any(signal in msg for signal in RATE_SIGNALS):
        raise RateLimitException(str(exc)) from exc
