"""
enrichment/nlp_extractor.py
────────────────────────────
Extracts a person's *current* company name from a LinkedIn snippet
when the original company no longer matches (job change detected).

Strategy:
  1. spaCy NER — look for ORG entities that are NOT the old company.
  2. Regex fallback — parse " at <Company>" patterns from the snippet.
  3. Returns "Unknown Company" if neither strategy finds anything.

The spaCy model is loaded lazily (once, then cached) so startup is fast
and every other module can import this file without triggering a load.
"""

import logging
from enrichment.utils import clean_company_name

logger = logging.getLogger(__name__)

_nlp = None  # Module-level cache — loaded once on first use


# ── Public API ───────────────────────────────────────────────────────────────

def load_nlp_model():
    """
    Load (or return cached) spaCy model.
    Raises RuntimeError with a clear fix message if the model is missing.
    """
    global _nlp
    if _nlp is not None:
        return _nlp

    import spacy
    try:
        _nlp = spacy.load("en_core_web_sm")
        logger.info("spaCy model loaded (en_core_web_sm)")
    except OSError as exc:
        raise RuntimeError(
            "spaCy model not found. Fix with:\n"
            "  python -m spacy download en_core_web_sm"
        ) from exc
    return _nlp


def extract_new_company_nlp(snippet: str, old_company: str) -> str:
    """
    Return the most likely *new* company name from a LinkedIn snippet.

    Parameters
    ----------
    snippet     : Raw text from a search result (title + body).
    old_company : The company name we already know (will be excluded).

    Returns
    -------
    str — new company name, or "Unknown Company" if nothing found.
    """
    nlp      = load_nlp_model()
    core_old = clean_company_name(old_company).lower()

    # ── Strategy 1: spaCy Named Entity Recognition ───────────────────────────
    doc  = nlp(snippet.title())
    orgs = [
        ent.text.strip()
        for ent in doc.ents
        if ent.label_ == "ORG" and core_old not in ent.text.lower()
    ]
    if orgs:
        logger.debug(f"NLP extracted: {orgs[0]!r}")
        return orgs[0]

    # ── Strategy 2: Regex " at <Company>" pattern ────────────────────────────
    lower = snippet.lower()
    if " at " in lower:
        after_at  = lower.split(" at ", 1)[1]
        candidate = (
            after_at
            .split(" - ")[0]
            .split(" | ")[0]
            .split(",")[0]
            .strip()
            .title()
        )
        if core_old not in candidate.lower() and len(candidate) > 3:
            logger.debug(f"Regex extracted: {candidate!r}")
            return candidate

    logger.debug("Could not extract new company name from snippet.")
    return "Unknown Company"
