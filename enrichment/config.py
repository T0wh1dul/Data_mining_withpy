"""
enrichment/config.py
────────────────────
Single source of truth for all settings.
Values are read from the .env file in the project root.
To change any setting, edit .env — never hardcode here.
"""

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()  # Reads .env from the current working directory

# ── File Paths ───────────────────────────────────────────────────────────────
INPUT_FILE  = Path(os.getenv("INPUT_FILE",  "Split_Data_Part_1.csv"))
OUTPUT_FILE = Path(os.getenv("OUTPUT_FILE", "Enriched_Data_Output_Ultimate.csv"))
MEMORY_FILE = OUTPUT_FILE.parent / "query_memory.json"
SEARCH_HISTORY_FILE = OUTPUT_FILE.parent / "search_history.jsonl"
EVENTS_FILE = OUTPUT_FILE.parent / "run_events.jsonl"
PIPELINE_PID_FILE = OUTPUT_FILE.parent / "pipeline.pid"
PIPELINE_RUNTIME_LOG = OUTPUT_FILE.parent / "pipeline_runtime.log"

# ── Timing ───────────────────────────────────────────────────────────────────
DELAY_SECONDS      = int(os.getenv("DELAY_SECONDS",      "15"))
BLOCK_WAIT_MINUTES = int(os.getenv("BLOCK_WAIT_MINUTES", "30"))

# ── Behaviour ────────────────────────────────────────────────────────────────
HEADLESS             = os.getenv("HEADLESS", "true").lower() == "true"
MIN_CONFIDENCE_SCORE = int(os.getenv("MIN_CONFIDENCE_SCORE", "60"))

# ── Domain / Industry Filters ────────────────────────────────────────────────
JUNK_DOMAINS: list[str] = [
    "linkedin.com", "facebook.com", "crunchbase.com", "bloomberg.com",
    "zoominfo.com", "glassdoor.com", "yelp.com", "yellowpages.com",
    "rocketreach.co", "upwork.com", "fiverr.com", "clutch.co",
    "goodfirms.co", "trustpilot.com", "g2.com", "capterra.com",
    "indeed.com", "twitter.com", "instagram.com", "youtube.com",
]

GENERIC_INDUSTRIES: list[str] = [
    "other industry", "other industries", "it services",
    "information technology", "business services", "consulting",
    "software", "other",
]

LOCATION_MAP: dict[str, str] = {
    "uk":             "United Kingdom",
    "us":             "United States",
    "uae":            "United Arab Emirates",
    "dr":             "Dominican Republic",
    "nv":             "Nevada",
    "tã¼rkiye":       "Turkey",
    "türkiye":        "Turkey",
    "phone interview": "",
    "europe":         "",
    "latin america":  "",
}
