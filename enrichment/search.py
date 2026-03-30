"""
enrichment/search.py
────────────────────
Low-level DuckDuckGo search wrapper with proxy support.

Improvements:
  • Exponential backoff on transient failures (2s → 4s → 8s)
  • RateLimitException is raised immediately without retrying
  • Proxy rotation per request with Bright Data/Oxylabs/SmartProxy support
  • Connectivity probe only fires when results are empty
  • Query validation and sanitization
  • Timeout handling for search requests
  • All retry decisions are centralised here
"""

import time
import logging
from typing import List, Dict, Optional
from ddgs import DDGS

from enrichment.monitor import log_event, log_search_event

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
MAX_RETRIES    = 3
RETRY_BACKOFF  = [2, 4, 8]   # seconds between attempts (exponential)
RATE_SIGNALS   = ("ratelimit", "202", "blocked", "too many requests", "429", "403")
QUERY_MIN_LENGTH = 3  # Minimum query length
QUERY_MAX_LENGTH = 500  # Maximum query length
SEARCH_TIMEOUT = 30  # seconds


class RateLimitException(Exception):
    """Raised when DuckDuckGo returns a rate-limit / IP-block response."""


# ── Public API ───────────────────────────────────────────────────────────────

def get_search_results(query: str, max_res: int = 10) -> List[Dict]:
    """
    Execute a DuckDuckGo text search with automatic retries and proxy rotation.

    Returns a (possibly empty) list of result dicts on success.
    Raises RateLimitException if DuckDuckGo blocks the request.
    Raises ValueError if query is invalid.
    """
    # Validate query
    if not query or not isinstance(query, str):
        logger.error(f"Invalid query: {query!r}")
        raise ValueError(f"Query must be non-empty string, got: {type(query)}")
    
    query = query.strip()
    if len(query) < QUERY_MIN_LENGTH:
        logger.error(f"Query too short ({len(query)} < {QUERY_MIN_LENGTH}): {query!r}")
        raise ValueError(f"Query must be at least {QUERY_MIN_LENGTH} characters")
    
    if len(query) > QUERY_MAX_LENGTH:
        logger.error(f"Query too long ({len(query)} > {QUERY_MAX_LENGTH})")
        query = query[:QUERY_MAX_LENGTH]
    
    # Try multiple times with exponential backoff
    for attempt in range(MAX_RETRIES):
        try:
            results = _fetch(query, max_res)
            return results
        except RateLimitException:
            raise   # Never retry a rate-limit — propagate immediately
        except Exception as exc:
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF[attempt]
                logger.warning(
                    f"Search attempt {attempt + 1}/{MAX_RETRIES} failed "
                    f"({exc.__class__.__name__}: {str(exc)[:80]}) — retrying in {wait}s"
                )
                time.sleep(wait)
            else:
                logger.error(f"All {MAX_RETRIES} attempts failed for query: {query!r}")
                raise

    return []


# ── Private Helpers ──────────────────────────────────────────────────────────

def _fetch(query: str, max_res: int) -> List[Dict]:
    """
    Single DDGS call with timeout.
    Raises RateLimitException or re-raises other errors.
    Supports proxy rotation if configured.
    """
    try:
        # Import proxy manager here to avoid circular imports
        from enrichment.proxy_manager import get_next_proxy, mark_proxy_failed, get_active_provider
        from enrichment import proxy_config
        
        proxy = get_next_proxy() if proxy_config.PROXY_SERVICE != "none" else None
        provider = get_active_provider()
        
        with DDGS(timeout=SEARCH_TIMEOUT, proxy=proxy) as ddgs:
            try:
                results = list(ddgs.text(query, max_results=max_res))
            except Exception as exc:
                # Mark proxy as failed before checking rate limit
                if proxy:
                    mark_proxy_failed(proxy)
                log_search_event(
                    query=query,
                    max_results=max_res,
                    status="error",
                    provider=provider,
                    error=str(exc),
                )
                log_event("search_error", level="warning", provider=provider, query=query, error=str(exc)[:200])
                _check_rate_limit(exc)
                raise
            
            # Validate results
            if not _validate_results(results):
                logger.warning(f"Invalid results for query {query!r}")
                raise ValueError("Search returned invalid result format")
            
            if not results:
                # Empty result could mean rate-limited; probe with a neutral query
                probe = list(ddgs.text("technology news", max_results=1))
                if not probe:
                    log_search_event(
                        query=query,
                        max_results=max_res,
                        status="rate_limited",
                        provider=provider,
                    )
                    log_event("rate_limit_detected", level="warning", provider=provider, query=query)
                    raise RateLimitException("Empty response on probe — likely rate limited.")

            log_search_event(
                query=query,
                max_results=max_res,
                status="ok",
                provider=provider,
                result_count=len(results),
            )
            return results
            
    except TimeoutError:
        logger.error(f"Search timeout ({SEARCH_TIMEOUT}s) for query: {query!r}")
        log_search_event(
            query=query,
            max_results=max_res,
            status="timeout",
            provider="unknown",
            error="timeout",
        )
        log_event("search_timeout", level="warning", query=query)
        raise RateLimitException(f"Search timeout - likely rate limited")
    except Exception as exc:
        # Re-raise if already a custom exception
        if isinstance(exc, (RateLimitException, ValueError)):
            raise
        logger.debug(f"Search error: {exc.__class__.__name__}: {exc}")
        raise


def _check_rate_limit(exc: Exception) -> None:
    """Raise RateLimitException if the exception looks like a block."""
    msg = str(exc).lower()
    if any(signal in msg for signal in RATE_SIGNALS):
        raise RateLimitException(str(exc)) from exc


def _validate_results(results: List[Dict]) -> bool:
    """Validate search results format."""
    if not isinstance(results, list):
        return False
    
    for res in results:
        if not isinstance(res, dict):
            return False
        # At minimum, should have 'href' (URL)
        if not res.get("href"):
            continue  # Allow some results to be incomplete
    
    return True
