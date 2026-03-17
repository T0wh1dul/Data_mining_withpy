"""
main.py
───────
Entry point — the only file you run:

    python main.py

Responsibilities:
  • Set up logging
  • Load config, memory, input CSV
  • Loop over unprocessed rows
  • Call search/NLP modules
  • Append results to output CSV row-by-row (crash-safe)
  • Handle rate-limit blocks gracefully
"""

import time
import random
import logging
import pandas as pd
from tqdm import tqdm
from datetime import datetime

from enrichment import config
from enrichment.memory import load_memory
from enrichment.nlp_extractor import extract_new_company_nlp, load_nlp_model
from enrichment.linkedin import smart_linkedin_search
from enrichment.website import smart_website_search
from enrichment.search import RateLimitException
from enrichment.utils import normalize_text


# ── Logging Setup ────────────────────────────────────────────────────────────

class ColoredFormatter(logging.Formatter):
    """Custom formatter with cleaner console output."""
    
    COLORS = {
        'DEBUG':    '\033[36m',      # Cyan
        'INFO':     '\033[32m',      # Green
        'WARNING':  '\033[33m',      # Yellow
        'ERROR':    '\033[31m',      # Red
        'CRITICAL': '\033[35m',      # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Only colorize for console output
        if isinstance(self.stream, logging.StreamHandler) or not hasattr(self, '_fmt'):
            color = self.COLORS.get(record.levelname, self.RESET)
            record.msg = f"{color}{record.msg}{self.RESET}"
        return super().format(record)


def setup_logging() -> None:
    """Setup logging with file + colored console output."""
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

# Will be populated after loading input file
OUTPUT_COLUMNS = []


def _init_output_file(input_df: pd.DataFrame) -> set:
    """
    Create the output CSV with headers if it doesn't exist.
    Preserves all input columns and adds enrichment columns.
    Returns a set of already-processed IDs so we can resume.
    """
    global OUTPUT_COLUMNS
    
    # Build output columns: all input columns + enrichment columns
    enrichment_cols = [
        "LinkedIn_URL", "Job_Status", "CSV_Website_Link",
        "Current_Company", "Current_Website_Link", "Confidence_%"
    ]
    OUTPUT_COLUMNS = list(input_df.columns) + enrichment_cols
    
    if config.OUTPUT_FILE.exists():
        out_df    = pd.read_csv(config.OUTPUT_FILE, dtype=str)
        processed = set(out_df["ID"].astype(str))
        return processed

    config.OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(config.OUTPUT_FILE, index=False)
    return set()


def _append_row(row_data: dict) -> None:
    """Append a single result row to the output CSV (no header)."""
    pd.DataFrame([row_data]).to_csv(
        config.OUTPUT_FILE, mode="a", header=False, index=False
    )


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
        print("\n" + "="*80)
        logger.info(f"Starting enrichment process")
        logger.info(f"Total rows: {self.total_rows} | Already processed: {skipped}")
        logger.info(f"Min confidence threshold: {config.MIN_CONFIDENCE_SCORE}%")
        print("="*80 + "\n")
    
    def display_summary(self):
        """Display final summary."""
        logger = logging.getLogger("main")
        percent = self.get_progress_percent()
        
        print("\n" + "="*80)
        logger.info(f"Processing complete!")
        logger.info(f"Total processed: {self.processed}/{self.total_rows} ({percent:.1f}%)")
        logger.info(f"High-confidence matches: {self.high_confidence}/{self.processed}")
        logger.info(f"Errors: {self.errors}")
        logger.info(f"Elapsed time: {self.get_elapsed_time()}")
        print("="*80 + "\n")


def _print_record_status(index: int, total: int, name: str, company: str, 
                         job_status: str, confidence: int):
    """Display status for current record in a clean format."""
    logger = logging.getLogger("main")
    percent = (index / total * 100) if total > 0 else 0
    
    # Status icon based on confidence
    if confidence >= config.MIN_CONFIDENCE_SCORE:
        icon = "✓"  # Green check
    else:
        icon = "⊗"  # Red X
    
    # Clean display
    logger.info(f"[{index:5d}/{total}] {icon} {name[:25]:25s} @ {company[:25]:25s} | "
                f"{job_status:20s} | {confidence:3d}%")


def _append_row(row_data: dict) -> None:
    """Append a single result row to the output CSV (no header)."""
    pd.DataFrame([row_data]).to_csv(
        config.OUTPUT_FILE, mode="a", header=False, index=False
    )


# ── Main Loop ────────────────────────────────────────────────────────────────

def main() -> None:
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("🚀 Enrichment script starting")

    # Fail fast if spaCy model is missing — better than crashing mid-run
    try:
        load_nlp_model()
    except RuntimeError as exc:
        logger.error(str(exc))
        return

    memory = load_memory()
    
    # Load input file first to determine output columns
    df = pd.read_csv(config.INPUT_FILE, encoding="latin-1", dtype=str)
    df.fillna("", inplace=True)
    
    processed = _init_output_file(df)  # Now has access to input columns

    remaining = df[~df["ID"].astype(str).isin(processed)]
    total_rows = len(remaining)

    if remaining.empty:
        logger.info("🎉 Nothing to do — all rows already processed!")
        return

    logger.info(f"Rows to process: {total_rows}  (skipped {len(processed)} already done)")

    processed_count = 0
    high_conf_count = 0

    for _, row in remaining.iterrows():
        row_id   = str(row["ID"])
        name     = normalize_text(str(row.get("Name",     "")).strip())
        company  = str(row.get("Company",  "")).strip()
        location = str(row.get("Location", "")).strip()
        industry = str(row.get("Industry", "")).strip()

        logger.info(f"── [{processed_count + 1}/{total_rows}] ID={row_id} | {name} @ {company}")

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

            # ── 4. Build output row with all input columns + enrichment ──────
            row_data = dict(row)  # Copy all original input columns
            row_data.update({
                "LinkedIn_URL":         linkedin_url,
                "Job_Status":           job_status,
                "CSV_Website_Link":     csv_website,
                "Current_Company":      current_company,
                "Current_Website_Link": current_website,
                "Confidence_%":         confidence,
            })
            _append_row(row_data)

            processed_count += 1
            if confidence >= config.MIN_CONFIDENCE_SCORE:
                high_conf_count += 1

            icon = "🟢" if confidence >= config.MIN_CONFIDENCE_SCORE else "🔴"
            logger.info(f"{icon} Saved | {job_status} | confidence={confidence}%")

        except RateLimitException:
            wait_sec = config.BLOCK_WAIT_MINUTES * 60
            logger.warning(
                f"⛔ Rate limited — sleeping {config.BLOCK_WAIT_MINUTES} min "
                f"({wait_sec}s) then resuming..."
            )
            time.sleep(wait_sec)
            # Row is NOT saved — will be retried on next loop iteration

        except Exception as exc:
            logger.error(
                f"Unexpected error on ID={row_id}: {exc}",
                exc_info=True,   # Prints full traceback to log file
            )
            # Continue to next row — don't let one bad row kill the run

    logger.info(
        f"🎉 Finished! Processed {processed_count}/{total_rows} rows. "
        f"High-confidence matches: {high_conf_count}/{processed_count}"
    )


if __name__ == "__main__":
    main()
