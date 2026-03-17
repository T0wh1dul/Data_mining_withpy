"""
enrichment/website.py
─────────────────────
Finds the official company website by scoring domain relevance.

Scoring logic:
    100  exact match  (domain_core == cleaned company name)
     90  partial match (one contains the other)
     50+ word match  (company words found in domain, +10 per word)
     <40 ignored      (threshold floor)

Stops early if a ≥90 score is found (perfect/near-perfect domain match).
"""

import re
import time
import random
import logging
from urllib.parse import urlparse

from enrichment import config
from enrichment.search import get_search_results
from enrichment.utils import clean_company_name, standardize_location

logger = logging.getLogger(__name__)

_SCORE_THRESHOLD  = 40   # Minimum acceptable domain score
_EARLY_STOP_SCORE = 90   # Stop searching if we hit this


def smart_website_search(company: str, location: str, industry: str) -> str:
    """
    Return the best-matching official website URL for a company,
    or "Not Found" if nothing meets the threshold.
    """
    logger.info(f"Website search → {company!r}")

    core      = clean_company_name(company)
    loc_std   = standardize_location(location)
    clean_ind = industry.lower() if industry.lower() not in config.GENERIC_INDUSTRIES else ""

    queries = [
        f"{core} {loc_std} {clean_ind} official site",
        f"{core} official website",
        f"{company} homepage",
    ]

    best_url    = "Not Found"
    best_score  = _SCORE_THRESHOLD  # Anything below this is ignored

    for q in queries:
        results = get_search_results(q, max_res=5)

        for res in results:
            url = res.get("href", "")
            if not url or _is_junk(url):
                continue

            score, clean_url = _score_domain(url, company, core)
            if score > best_score:
                best_score = score
                best_url   = clean_url
                logger.debug(f"New best website: {clean_url} (score={score})")

        if best_score >= _EARLY_STOP_SCORE:
            logger.info(f"Early stop — domain score {best_score}% for {best_url}")
            break

        _polite_sleep()

    return best_url


# ── Private Helpers ──────────────────────────────────────────────────────────

def _is_junk(url: str) -> bool:
    return any(junk in url.lower() for junk in config.JUNK_DOMAINS)


def _score_domain(url: str, company: str, core: str) -> tuple[int, str]:
    """
    Returns (score, clean_root_url).
    score = 0 if the URL can't be parsed.
    """
    try:
        parsed      = urlparse(url)
        domain_core = parsed.netloc.lower().replace("www.", "").split(".")[0]
        comp_clean  = re.sub(r"[^a-z0-9]", "", core.lower())
        clean_url   = f"{parsed.scheme}://{parsed.netloc}"

        if comp_clean == domain_core:
            return 100, clean_url
        if comp_clean in domain_core or domain_core in comp_clean:
            return 90, clean_url

        # Word-level partial match
        words   = [re.sub(r"[^a-z0-9]", "", w) for w in company.lower().replace("'", "").split()]
        words   = [w for w in words if len(w) > 2]
        matched = sum(1 for w in words if w in domain_core)
        score   = (50 + matched * 10) if matched > 0 else 0

        return score, clean_url
    except Exception as exc:
        logger.debug(f"URL parse error for {url!r}: {exc}")
        return 0, ""


def _polite_sleep() -> None:
    jitter = random.uniform(-3, 5)
    time.sleep(max(1, config.DELAY_SECONDS + jitter))
