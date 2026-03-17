"""
enrichment/utils.py
───────────────────
Pure helper functions — no I/O, no side-effects.
All functions here are stateless and independently testable.
"""

import re
import unicodedata
import logging
from enrichment import config

logger = logging.getLogger(__name__)


# ── Text Normalisation ───────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """Strip accents and convert to plain ASCII."""
    return (
        unicodedata.normalize("NFKD", str(text))
        .encode("ascii", "ignore")
        .decode("utf-8")
        .strip()
    )


def standardize_location(location: str) -> str:
    """Expand abbreviations (e.g. 'uk' → 'United Kingdom') via LOCATION_MAP."""
    return config.LOCATION_MAP.get(str(location).lower().strip(), str(location).strip())


def clean_company_name(company: str) -> str:
    """
    Strip legal suffixes so 'Acme Ltd.' and 'Acme' are treated as the same entity.
    Returns the cleaned core name (lowercase, ASCII).
    """
    company_str = str(company).lower().strip()
    suffix_pattern = (
        r"(?:\s*[,.]?\s*\b"
        r"(?:ltd|limited|llc|inc|corp|corporation|co|company|"
        r"technologies|tech|group|holdings|intl|int\'l)"
        r"\b\.?)+$"
    )
    core = re.sub(suffix_pattern, "", company_str).strip()
    return normalize_text(core) if core else company_str


# ── Matching Helpers ─────────────────────────────────────────────────────────

def is_smart_match(target_name: str, text: str) -> bool:
    """
    Returns True only if every word in target_name appears in text.
    More reliable than a simple substring check for multi-word names.
    """
    parts = normalize_text(target_name.lower()).replace("-", " ").split()
    return all(part in normalize_text(text.lower()) for part in parts)


def check_past_employment(company: str, text: str) -> bool:
    """Detect signals that someone no longer works at company."""
    past_keywords = [
        "former", "past", "previously", "previous",
        "ex-", "left", "departed", "alumni",
    ]
    text_lower = normalize_text(text.lower())
    core = clean_company_name(company)
    for kw in past_keywords:
        if re.search(rf"{kw}.*?\b{re.escape(core)}\b", text_lower):
            return True
    return False


# ── Confidence Scoring ───────────────────────────────────────────────────────

def score_profile(
    name: str,
    company: str,
    location: str,
    industry: str,
    title: str,
    snippet: str,
) -> int:
    """
    Score a LinkedIn search result 0-100.

    Breakdown:
        +40  name found in title/snippet
        +30  company found in title/snippet
        +15  location found (if non-empty)
        +15  non-generic industry found
    """
    score = 0
    full = normalize_text(f"{title} {snippet}").lower()

    if is_smart_match(name, full):
        score += 40
    if clean_company_name(company) in full:
        score += 30
    if location and location.lower() in full:
        score += 15
    if (
        industry.lower() not in config.GENERIC_INDUSTRIES
        and industry.lower() in full
    ):
        score += 15

    return min(score, 100)
