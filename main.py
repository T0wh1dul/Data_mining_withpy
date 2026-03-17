"""
main.py
───────
Entry point — the only file you run:

    python main.py

Responsibilities:
  • Set up clean logging
  • Load config, memory, input CSV
  • Filter unwanted columns
  • Loop over unprocessed rows with progress tracking
  • Call search/NLP modules
  • Append results to output CSV row-by-row (crash-safe)
  • Handle rate-limit blocks gracefully
"""

import time
import random
import logging
import pandas as pd
from datetime import datetime

from enrichment import config
from enrichment.memory import load_memory
from enrichment.nlp_extractor import extract_new_company_nlp, load_nlp_model
from enrichment.linkedin import smart_linkedin_search
from enrichment.website import smart_website_search
from enrichment.search import RateLimitException
from enrichment.utils import normalize_text


# ── Configuration ────────────────────────────────────────────────────────────

COLUMNS_TO_EXCLUDE = {
    "Price Range", "Timeline", "Review Summary", 
    "Rating", "Review Date", "Data Source"
}

COLUMNS_TO_KEEP = [
    "ID", "Name", "Position", "Company", "Industry", 
    "Location", "Company Size", "Category"
]


# ── Logging Setup ────────────────────────────────────────────────────────────

def setup_logging() -> None:
    """Setup logging with file + clean console output."""
    # File handler - detailed format with timestamps
    file_fmt = "%(asctime)s | %(levelname)-8s | %(name)-18s | %(message)s"
    file_handler = logging.FileHandler("enrichment.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(file_fmt))
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler - clean format, only INFO and above
    console_fmt = "%(message)s"
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(console_fmt))
    console_handler.setLevel(logging.INFO)
    
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler, console_handler],
    )
    
    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "ddgs", "urllib3", "selenium", "primp"):
        logging.getLogger(noisy).setLevel(logging.ERROR)


# ── CSV Helpers ──────────────────────────────────────────────────────────────

OUTPUT_COLUMNS = []


def _filter_columns(input_df: pd.DataFrame) -> list:
    """
    Build the list of columns to keep in output.
    - Keep specified columns from input
    - Exclude unwanted columns
    - Add enrichment columns
    """
    # Keep only columns that exist and are not excluded
    kept_cols = [col for col in input_df.columns 
                 if col in COLUMNS_TO_KEEP or col not in COLUMNS_TO_EXCLUDE]
    
    # Add enrichment columns
    enrichment_cols = [
        "LinkedIn_URL", "Job_Status", "CSV_Website_Link",
        "Current_Company", "Current_Website_Link", "Confidence_%"
    ]
    
    return kept_cols + enrichment_cols


def _init_output_file(input_df: pd.DataFrame) -> set:
    """
    Create the output CSV with headers if it doesn't exist.
    Keeps only essential columns and adds enrichment data.
    Returns a set of already-processed IDs so we can resume.
    """
    global OUTPUT_COLUMNS
    OUTPUT_COLUMNS = _filter_columns(input_df)
    
    if config.OUTPUT_FILE.exists():
        out_df = pd.read_csv(config.OUTPUT_FILE, dtype=str)
        processed = set(out_df["ID"].astype(str))
        return processed

    config.OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(config.OUTPUT_FILE, index=False)
    return set()


def _append_row(row_data: dict) -> None:
    """Append a single result row to the output CSV (no header)."""
    # Filter to keep only desired columns
    filtered_data = {k: v for k, v in row_data.items() if k in OUTPUT_COLUMNS}
    pd.DataFrame([filtered_data]).to_csv(
        config.OUTPUT_FILE, mode="a", header=False, index=False
    )


# ── Input Validation ────────────────────────────────────────────────────────

def _validate_row_data(row_id: str, name: str, company: str, location: str, industry: str) -> tuple[bool, str]:
    """
    Validate that row has minimum required fields.
    Returns (is_valid, error_message)
    """
    if not name or len(name.strip()) < 2:
        return False, f"ID {row_id}: Name too short or empty"
    
    if not company or len(company.strip()) < 2:
        return False, f"ID {row_id}: Company too short or empty"
    
    return True, ""


def _validate_linkedin_url(url: str) -> bool:
    """Validate that URL looks like a LinkedIn profile."""
    if url == "Not Found":
        return True  # Not Found is valid
    
    if not url or not isinstance(url, str):
        return False
    
    return "linkedin.com/in/" in url.lower() or url == "Not Found"


def _validate_website_url(url: str) -> bool:
    """Validate that URL is properly formatted."""
    if url == "Not Found":
        return True  # Not Found is valid
    
    if not url or not isinstance(url, str):
        return False
    
    # Should start with http/https or be "Not Found"
    return url.startswith(("http://", "https://")) or url == "Not Found"


def _safe_sleep(delay_seconds: int, jitter_range: tuple = (-3, 5)):
    """
    Sleep for specified seconds with optional jitter.
    Ensures minimum sleep time of 1 second.
    """
    if delay_seconds < 0:
        delay_seconds = 1
    
    min_jitter, max_jitter = jitter_range
    jitter = random.uniform(min_jitter, max_jitter)
    sleep_time = max(1, delay_seconds + jitter)
    time.sleep(sleep_time)


# ── CSV Write Helper ─────────────────────────────────────────────────────────

def _append_row_safe(row_data: dict, max_retries: int = 3) -> bool:
    """
    Safely append a row to output CSV with retry logic.
    Returns True on success, False on failure.
    """
    for attempt in range(max_retries):
        try:
            _append_row(row_data)
            return True
        except Exception as exc:
            if attempt < max_retries - 1:
                logger = logging.getLogger("main")
                logger.warning(f"CSV write failed (attempt {attempt+1}/{max_retries}), retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger = logging.getLogger("main")
                logger.error(f"CSV write failed after {max_retries} attempts: {str(exc)[:100]}")
                return False
    
    return False


# ── Statistics & Monitoring ──────────────────────────────────────────────────

class ProcessingStats:
    """Track and display processing statistics."""
    
    def __init__(self, total_rows: int):
        self.total_rows = total_rows
        self.processed = 0
        self.high_confidence = 0
        self.errors = 0
        self.start_time = datetime.now()
    
    def add_success(self, confidence: int):
        """Record successful processing."""
        self.processed += 1
        if confidence >= config.MIN_CONFIDENCE_SCORE:
            self.high_confidence += 1
    
    def add_error(self):
        """Record processing error."""
        self.errors += 1
    
    def get_progress_percent(self) -> float:
        """Get percentage complete."""
        return (self.processed / self.total_rows * 100) if self.total_rows > 0 else 0
    
    def get_elapsed_time(self) -> str:
        """Get formatted elapsed time."""
        elapsed = datetime.now() - self.start_time
        hours = elapsed.seconds // 3600
        minutes = (elapsed.seconds % 3600) // 60
        seconds = elapsed.seconds % 60
        return f"{hours}h {minutes}m {seconds}s"
    
    def display_header(self, skipped: int):
        """Display processing summary header."""
        logger = logging.getLogger("main")
        print("\n" + "*"*80)
        print("  DATA ENRICHMENT PIPELINE - LinkedIn & Website Finder".center(80))
        print("*"*80)
        logger.info(f"Starting enrichment process")
        logger.info(f"Total rows to process: {self.total_rows} | Already processed: {skipped}")
        logger.info(f"Min confidence threshold: {config.MIN_CONFIDENCE_SCORE}%")
        logger.info(f"Output columns: {', '.join(OUTPUT_COLUMNS)}")
        print("*"*80)
        print("ID      | Status      | Name                  | Company              | Confidence")
        print("-"*80 + "\n")
    
    def display_summary(self):
        """Display final summary."""
        logger = logging.getLogger("main")
        percent = self.get_progress_percent()
        
        print("\n" + "*"*80)
        print("  PROCESSING COMPLETE".center(80))
        print("*"*80)
        logger.info(f"Total processed: {self.processed}/{self.total_rows} ({percent:.1f}%)")
        if self.processed > 0:
            match_percent = (self.high_confidence / self.processed * 100)
            logger.info(f"High-confidence matches: {self.high_confidence} ({match_percent:.1f}% of processed)")
        logger.info(f"Errors encountered: {self.errors}")
        logger.info(f"Elapsed time: {self.get_elapsed_time()}")
        print("*"*80 + "\n")


def _print_record_status(index: int, total: int, row_id: str, name: str, company: str,
                        job_status: str, confidence: int):
    """Display status for current record in a clean, tabular format."""
    logger = logging.getLogger("main")
    
    # Status icon based on confidence (using ASCII-safe characters)
    icon = "Y" if confidence >= config.MIN_CONFIDENCE_SCORE else "N"
    
    # Truncate long fields to fit in table
    name_short = name[:20].ljust(20)
    company_short = company[:18].ljust(18)
    status_short = job_status[:12].ljust(12)
    
    logger.info(f"{row_id:7s} | {icon} {status_short} | {name_short} | {company_short} | {confidence:3d}%")


# ── Main Loop ────────────────────────────────────────────────────────────────

def main() -> None:
    setup_logging()
    logger = logging.getLogger("main")

    # Fail fast if spaCy model is missing
    try:
        load_nlp_model()
        logger.info("✓ spaCy model loaded successfully")
    except RuntimeError as exc:
        logger.error(f"✗ {str(exc)}")
        return

    memory = load_memory()
    
    # Load input file first
    logger.info(f"Loading input file: {config.INPUT_FILE}")
    try:
        df = pd.read_csv(config.INPUT_FILE, encoding="latin-1", dtype=str)
        df.fillna("", inplace=True)
        logger.info(f"✓ Loaded {len(df)} total records from input")
    except FileNotFoundError:
        logger.error(f"✗ Input file not found: {config.INPUT_FILE}")
        return
    except Exception as exc:
        logger.error(f"✗ Error reading input file: {str(exc)}")
        return
    
    processed = _init_output_file(df)
    remaining = df[~df["ID"].astype(str).isin(processed)]
    total_rows = len(remaining)

    if remaining.empty:
        logger.info("\n✓ All rows already processed! Nothing to do.\n")
        return

    # Create stats tracker
    stats = ProcessingStats(total_rows)
    stats.display_header(len(processed))

    for idx, (_, row) in enumerate(remaining.iterrows(), start=1):
        row_id   = str(row["ID"])
        name     = normalize_text(str(row.get("Name", "")).strip())
        company  = str(row.get("Company", "")).strip()
        location = str(row.get("Location", "")).strip()
        industry = str(row.get("Industry", "")).strip()

        try:
            # ── 1. Find LinkedIn profile ─────────────────────────────────────
            linkedin_url, snippet, job_status, confidence = smart_linkedin_search(
                name, company, location, industry, memory
            )

            # Brief pause between LinkedIn and website searches
            time.sleep(config.DELAY_SECONDS + random.uniform(-3, 5))

            # ── 2. Find company website ──────────────────────────────────────
            csv_website      = smart_website_search(company, location, industry)
            current_company  = company
            current_website  = csv_website

            # ── 3. Resolve new company if job change detected ────────────────
            if job_status == "Match but need update":
                current_company = extract_new_company_nlp(snippet, company)
                if current_company != "Unknown Company":
                    current_website = smart_website_search(current_company, location, industry)

            # ── 4. Build output row - keep only desired columns + enrichment ──
            row_data = {}
            
            # Keep only specified columns from input
            for col in OUTPUT_COLUMNS:
                if col in row.index and col not in ["LinkedIn_URL", "Job_Status", 
                                                     "CSV_Website_Link", "Current_Company",
                                                     "Current_Website_Link", "Confidence_%"]:
                    row_data[col] = str(row[col])
            
            # Add enrichment columns
            row_data.update({
                "LinkedIn_URL":         linkedin_url,
                "Job_Status":           job_status,
                "CSV_Website_Link":     csv_website,
                "Current_Company":      current_company,
                "Current_Website_Link": current_website,
                "Confidence_%":         confidence,
            })
            
            _append_row(row_data)

            stats.add_success(confidence)
            _print_record_status(idx, total_rows, row_id, name, company, job_status, confidence)

        except RateLimitException:
            wait_sec = config.BLOCK_WAIT_MINUTES * 60
            print("\n" + "-"*80)
            logger.warning(
                f"Rate limited! Waiting {config.BLOCK_WAIT_MINUTES} minutes before resuming..."
            )
            logger.warning(f"Resume time: {datetime.now().strftime('%H:%M:%S')}")
            print("-"*80 + "\n")
            time.sleep(wait_sec)

        except Exception as exc:
            stats.add_error()
            error_msg = str(exc)[:80]
            logger.error(f"✗ Error on ID {row_id}: {error_msg}")

    stats.display_summary()
    logger.info(f"✓ Output file: {config.OUTPUT_FILE}")
    logger.info(f"✓ Detailed logs: enrichment.log")
    logger.info(f"✓ Columns in output: {len(OUTPUT_COLUMNS)}\n")


if __name__ == "__main__":
    main()
