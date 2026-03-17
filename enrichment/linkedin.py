"""
enrichment/linkedin.py
──────────────────────
Two-phase LinkedIn profile search.

Phase 1  — 3 highest-weighted exact/quoted queries.
Phase 2  — 2 highest-weighted looser queries (fallback only).

Both phases stop early the moment MIN_CONFIDENCE_SCORE is reached.
After a successful match the winning query's weight is incremented so
it gets sorted first in future runs (adaptive learning).
"""

import time
import random
import logging
from typing import Dict, List, Set, Tuple

from enrichment import config
from enrichment.memory import save_memory
from enrichment.search import get_search_results
from enrichment.utils import (
    check_past_employment,
    clean_company_name,
    normalize_text,
    score_profile,
    standardize_location,
)

logger = logging.getLogger(__name__)


# ── Public API ───────────────────────────────────────────────────────────────

def smart_linkedin_search(
    name: str,
    company: str,
    location: str,
    industry: str,
    memory: Dict[int, int],
) -> Tuple[str, str, str, int]:
    """
    Search LinkedIn for a person and return:
        (linkedin_url, snippet, job_status, confidence_score)

    job_status values:
        "Matched"               — high confidence, still at company
        "Match but need update" — high confidence, may have moved on
        "Low Confidence Match"  — best score < MIN_CONFIDENCE_SCORE
        "Not Found"             — zero candidates returned
    """
    logger.info(f"LinkedIn search → {name!r} @ {name!r}")

    name_norm   = normalize_text(name)
    core_co     = clean_company_name(company)
    loc_std     = standardize_location(location)
    clean_ind   = industry.lower() if industry.lower() not in config.GENERIC_INDUSTRIES else ""

    phase_1: List[Tuple[int, str]] = [
        (0, f'"{name_norm}" "{core_co}" {loc_std} {clean_ind} site:linkedin.com/in/'),
        (1, f'"{name_norm}" "{core_co}" {loc_std} site:linkedin.com/in/'),
        (2, f'"{name_norm}" {core_co} {loc_std} {clean_ind} site:linkedin.com/in/'),
        (3, f'"{name_norm}" {core_co} {loc_std} site:linkedin.com/in/'),
        (4, f'"{name_norm}" {core_co} site:linkedin.com/in/'),
        (5, f'{name_norm} "{core_co}" {loc_std} site:linkedin.com/in/'),
    ]
    phase_2: List[Tuple[int, str]] = [
        (6, f'{name_norm} {core_co} {loc_std} site:linkedin.com/in/'),
        (7, f'{name_norm} {core_co} site:linkedin.com/in/'),
        (8, f'{name_norm} {company} {loc_std} site:linkedin.com/in/'),
        (9, f'{name_norm} {company} site:linkedin.com/in/'),
    ]

    # Sort each phase so historically successful queries run first
    phase_1.sort(key=lambda x: memory.get(x[0], 0), reverse=True)
    phase_2.sort(key=lambda x: memory.get(x[0], 0), reverse=True)

    candidates: List[Dict] = []
    seen_urls:  Set[str]   = set()

    best_p1 = _run_phase(
        queries=phase_1[:3],
        phase_name="Phase 1",
        name=name, company=company, loc_std=loc_std, industry=industry,
        candidates=candidates, seen_urls=seen_urls, memory=memory,
    )

    if best_p1 < config.MIN_CONFIDENCE_SCORE:
        logger.info(f"Phase 1 best={best_p1}% — starting Phase 2 fallback")
        _run_phase(
            queries=phase_2[:2],
            phase_name="Phase 2",
            name=name, company=company, loc_std=loc_std, industry=industry,
            candidates=candidates, seen_urls=seen_urls, memory=memory,
        )

    if not candidates:
        return "Not Found", "No Snippet", "Not Found", 0

    best = max(candidates, key=lambda c: c["score"])
    logger.info(f"Best match → Q{best['q_id']} | score={best['score']}%")

    # Reward the winning query pattern
    if best["score"] >= config.MIN_CONFIDENCE_SCORE:
        memory[best["q_id"]] = memory.get(best["q_id"], 0) + 1
        save_memory(memory)

    job_status = _determine_job_status(best, company)
    return best["url"], best["snippet"], job_status, best["score"]


# ── Private Helpers ──────────────────────────────────────────────────────────

def _run_phase(
    queries: List[Tuple[int, str]],
    phase_name: str,
    name: str,
    company: str,
    loc_std: str,
    industry: str,
    candidates: List[Dict],
    seen_urls: Set[str],
    memory: Dict[int, int],
) -> int:
    """
    Execute a list of queries, collecting candidates.
    Returns the best score seen so far (across all phases).
    Stops early if MIN_CONFIDENCE_SCORE is reached.
    """
    for attempt, (q_id, query) in enumerate(queries, 1):
        query = query.strip()
        logger.debug(
            f"[{attempt}/{len(queries)}] {phase_name} | "
            f"weight={memory.get(q_id, 0)} | Q{q_id} | {query!r}"
        )

        results = get_search_results(query)

        for res in results:
            url = res.get("href", "")
            if "linkedin.com/in/" not in url or url in seen_urls:
                continue
            seen_urls.add(url)

            title   = res.get("title", "")
            snippet = res.get("body", "")
            score   = score_profile(name, company, loc_std, industry, title, snippet)
            candidates.append({"url": url, "snippet": snippet, "score": score, "q_id": q_id})

        best_now = max((c["score"] for c in candidates), default=0)
        if best_now >= config.MIN_CONFIDENCE_SCORE:
            logger.info(f"Early stop in {phase_name} — best score {best_now}%")
            return best_now

        _polite_sleep()

    return max((c["score"] for c in candidates), default=0)


def _determine_job_status(best: Dict, company: str) -> str:
    """Map a candidate result to a human-readable job status string."""
    score   = best["score"]
    snippet = best["snippet"]

    if score < config.MIN_CONFIDENCE_SCORE:
        return "Low Confidence Match"

    still_there = (
        clean_company_name(company) in normalize_text(snippet).lower()
        and not check_past_employment(company, snippet)
    )
    return "Matched" if still_there else "Match but need update"


def _polite_sleep() -> None:
    """Sleep for DELAY_SECONDS ± a small random jitter to appear less bot-like."""
    jitter = random.uniform(-3, 5)
    time.sleep(max(1, config.DELAY_SECONDS + jitter))
