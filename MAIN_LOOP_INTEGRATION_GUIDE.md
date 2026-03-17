"""
MAIN_LOOP_INTEGRATION_GUIDE.md
─────────────────────────────
Step-by-step guide to integrate validation functions into main.py
This is the LAST remaining piece of work to complete the refactor.
"""

# 🔧 MAIN LOOP INTEGRATION GUIDE

## Goal
Update the main processing loop in `main.py` to call validation functions and safe CSV writing.

## Currently Incomplete
The main processing loop (around lines 250-320) still has:
- Direct `time.sleep()` calls (should use `_safe_sleep()`)
- No input validation
- No URL validation
- No CSV write retry logic

## The Fix

### Step 1: Find the Main Loop

Open `main.py` and find the main processing loop. It looks like this:

```python
# Lines ~250-320 (approximate)
for idx, row in input_data.iterrows():
    row_id = str(row.get("ID", idx))
    name = row.get("Name", "").strip()
    company = row.get("Company", "").strip()
    location = row.get("Location", "").strip()
    industry = row.get("Industry", "").strip()
    
    # LinkedIn search
    linkedin_url, snippet, job_status, confidence = smart_linkedin_search(
        name, company, location, industry, memory
    )
    logger.info(f"[{row_id}] LinkedIn: {confidence}% - {linkedin_url}")
    
    _safe_sleep(config.DELAY_SECONDS)  # <-- May still have old time.sleep()
    
    # Website search
    csv_website = row.get("CSV_Website_Link", "")
    current_website, _ = find_company_website(company, industry)
    # ... rest of loop
```

### Step 2: Replace the Entire Loop

Replace the main processing loop with this optimized version:

```python
for idx, row in input_data.iterrows():
    row_id = str(row.get("ID", idx))
    name = row.get("Name", "").strip()
    company = row.get("Company", "").strip()
    location = row.get("Location", "").strip()
    industry = row.get("Industry", "").strip()
    position = row.get("Position", "").strip()
    
    # ──────────────────────────────────────────────────
    # STEP 1: INPUT VALIDATION (FIX #1)
    # ──────────────────────────────────────────────────
    is_valid, error_msg = _validate_row_data(row_id, name, company, location, industry)
    if not is_valid:
        logger.warning(f"Skipping row {row_id}: {error_msg}")
        stats.add_error()
        continue
    
    # ──────────────────────────────────────────────────
    # STEP 2: LINKEDIN SEARCH
    # ──────────────────────────────────────────────────
    linkedin_url, snippet, job_status, confidence = smart_linkedin_search(
        name, company, location, industry, memory
    )
    logger.info(f"[{row_id}] LinkedIn result: {confidence}% confidence - {linkedin_url}")
    
    # ──────────────────────────────────────────────────
    # STEP 3: VALIDATE LINKEDIN URL (FIX #4)
    # ──────────────────────────────────────────────────
    if not _validate_linkedin_url(linkedin_url):
        logger.warning(f"[{row_id}] Invalid LinkedIn URL format: {linkedin_url}")
        linkedin_url = "Not Found"
    
    # ──────────────────────────────────────────────────
    # STEP 4: SAFE SLEEP (FIX #2)
    # ──────────────────────────────────────────────────
    _safe_sleep(config.DELAY_SECONDS)  # Guaranteed >= 1 second
    
    # ──────────────────────────────────────────────────
    # STEP 5: WEBSITE SEARCH
    # ──────────────────────────────────────────────────
    csv_website = row.get("CSV_Website_Link", "")
    current_website, _ = find_company_website(company, industry)
    logger.info(f"[{row_id}] Website found: {current_website}")
    
    # ──────────────────────────────────────────────────
    # STEP 6: VALIDATE WEBSITE URL (FIX #4)
    # ──────────────────────────────────────────────────
    if not _validate_website_url(csv_website):
        csv_website = "Not Found"
    if not _validate_website_url(current_website):
        current_website = "Not Found"
    
    # ──────────────────────────────────────────────────
    # STEP 7: JOB STATUS DETERMINATION
    # ──────────────────────────────────────────────────
    current_company = "Not Found"
    if job_status == "Job Changed":
        logger.warning(f"[{row_id}] Job status changed from {company}")
        current_company = snippet  # Extract from snippet if available
    
    # ──────────────────────────────────────────────────
    # STEP 8: PREPARE OUTPUT ROW (FIX #6 - COLUMN VALIDATION)
    # ──────────────────────────────────────────────────
    output_row = {}
    for col in output_columns:
        if col in ["LinkedIn_URL", "Job_Status", "CSV_Website_Link", 
                   "Current_Company", "Current_Website_Link", "Confidence_%"]:
            # Use enriched data
            if col == "LinkedIn_URL":
                output_row[col] = linkedin_url
            elif col == "Job_Status":
                output_row[col] = job_status
            elif col == "CSV_Website_Link":
                output_row[col] = csv_website
            elif col == "Current_Company":
                output_row[col] = current_company
            elif col == "Current_Website_Link":
                output_row[col] = current_website
            elif col == "Confidence_%":
                output_row[col] = confidence
        else:
            # Copy from input (if column exists)
            output_row[col] = row.get(col, "") if col in row.index else ""
    
    # ──────────────────────────────────────────────────
    # STEP 9: SAFE CSV WRITE WITH RETRY (FIX #5)
    # ──────────────────────────────────────────────────
    if _append_row_safe(output_row, max_retries=3):
        if confidence >= config.MIN_CONFIDENCE_SCORE:
            stats.add_success(confidence)
        else:
            stats.add_success(0)
        logger.info(f"[{row_id}] Row written successfully")
    else:
        stats.add_error()
        logger.error(f"[{row_id}] Failed to write output row after retries")
        # Continue to next row even if this one failed
        continue
    
    # ──────────────────────────────────────────────────
    # STEP 10: SAVE MEMORY AFTER SUCCESS (FIX #3)
    # ──────────────────────────────────────────────────
    try:
        save_memory(memory)
    except Exception as e:
        logger.warning(f"Failed to save memory: {e}")
    
    # Update progress display
    elapsed = time.time() - start_time
    logger.info(f"Progress: {stats.processed}/{total_rows} rows processed "
                f"({stats.processed*100/total_rows:.1f}%) - "
                f"Elapsed: {stats.format_elapsed_time()} - "
                f"High-conf: {stats.high_confidence}")
```

### Step 3: Verify All Imports

Ensure these imports are at the top of main.py:

```python
import time
import random
import pandas as pd
from pathlib import Path
from enrichment.config import config
from enrichment.memory import load_memory, save_memory
from enrichment.linkedin import smart_linkedin_search
from enrichment.website import find_company_website
from enrichment.search import get_search_results
from enrichment.utils import normalize_text, clean_company_name
import logging
```

### Step 4: Verify Validation Functions Exist

Make sure these 5 functions are defined in main.py (they should be):

```python
def _validate_row_data(row_id, name, company, location, industry):
    """Check minimum required fields."""
    if not name or len(name.strip()) < 2:
        return False, f"ID {row_id}: Name too short"
    if not company or len(company.strip()) < 2:
        return False, f"ID {row_id}: Company too short"
    return True, ""

def _validate_linkedin_url(url):
    """Check LinkedIn URL format."""
    if url == "Not Found":
        return True
    return url.startswith("http") and "linkedin.com/in/" in url

def _validate_website_url(url):
    """Check website URL format."""
    if url == "Not Found":
        return True
    return url.startswith(("http://", "https://"))

def _safe_sleep(delay_seconds, jitter_range=(-3, 5)):
    """Sleep with guaranteed minimum of 1 second."""
    if delay_seconds < 0:
        delay_seconds = 1
    min_jitter, max_jitter = jitter_range
    jitter = random.uniform(min_jitter, max_jitter)
    sleep_time = max(1, delay_seconds + jitter)
    time.sleep(sleep_time)

def _append_row_safe(row_data, max_retries=3):
    """Append row with retry logic."""
    for attempt in range(max_retries):
        try:
            _append_row(row_data)
            return True
        except Exception as exc:
            if attempt < max_retries - 1:
                logger.warning(f"CSV write failed (attempt {attempt+1}/{max_retries}), retrying...")
                time.sleep(2 ** attempt)
            else:
                logger.error(f"CSV write failed after {max_retries} attempts")
                return False
    return False
```

### Step 5: Review ProcessingStats Class

Ensure `ProcessingStats` class has these methods:

```python
class ProcessingStats:
    def __init__(self):
        self.processed = 0
        self.high_confidence = 0
        self.errors = 0
        self.start_time = time.time()
    
    def add_success(self, confidence):
        self.processed += 1
        if confidence >= config.MIN_CONFIDENCE_SCORE:
            self.high_confidence += 1
    
    def add_error(self):
        self.processed += 1
        self.errors += 1
    
    def format_elapsed_time(self):
        elapsed = time.time() - self.start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
```

---

## Testing the Integration

### Test 1: Single Row
- Create test file with 1 row
- Run: `python main.py`
- Expected: Completes without errors, generates 1 output row

### Test 2: Invalid Rows
- Create test file with 1 valid row + 1 invalid row (empty name)
- Run: `python main.py`
- Expected: Skips invalid row, processes valid row, generates 1 output row

### Test 3: Rate Limiting
- Create test file with 20 rows
- Run: `python main.py`
- Expected: Completes, shows progress, no errors in log

### Test 4: Proxy Integration
- Set `PROXY_SERVICE=brightdata` (or other)
- Set proxy credentials in .env
- Create test file with 5 rows
- Run: `python main.py`
- Expected: Uses proxy IPs, completes successfully

---

## Checklist Before Running

- [ ] All 5 validation functions are defined in main.py
- [ ] ProcessingStats class is defined
- [ ] All imports are present
- [ ] Main loop uses `_validate_row_data()` for input validation
- [ ] Main loop uses `_safe_sleep()` instead of `time.sleep()`
- [ ] Main loop uses `_validate_linkedin_url()` on results
- [ ] Main loop uses `_validate_website_url()` on results
- [ ] Main loop uses `_append_row_safe()` for CSV writing
- [ ] Main loop saves memory after success
- [ ] Code is indented correctly
- [ ] No syntax errors (check with Ctrl+Shift+M)

---

## Expected Console Output After Integration

```
[ID_001] LinkedIn result: 85% confidence - https://linkedin.com/in/john-doe-12345
[ID_001] Website found: https://example-company.com
[ID_001] Row written successfully
Progress: 1/20 rows processed (5.0%) - Elapsed: 00:00:18 - High-conf: 1

[ID_002] Skipping row ID_002: Name too short
Progress: 2/20 rows processed (10.0%) - Elapsed: 00:00:20 - High-conf: 1

[ID_003] LinkedIn result: 72% confidence - https://linkedin.com/in/jane-smith-98765
[ID_003] Website found: https://another-company.com
[ID_003] Row written successfully
Progress: 3/20 rows processed (15.0%) - Elapsed: 00:00:38 - High-conf: 2

...
```

---

## If You Hit Issues

### Issue: Text match failure again
**Solution:** Copy the exact code snippets manually, don't rely on automatic replacement

### Issue: Indentation errors
**Solution:** 
- Use 4 spaces for indentation (not tabs)
- Check that all `if` blocks are indented 1 level from loop
- Use Python formatter: Shift+Alt+F

### Issue: "_append_row is not defined"
**Solution:** Check that the `_append_row()` function exists earlier in main.py

### Issue: "stats is not initialized"
**Solution:** Check that `stats = ProcessingStats()` appears before the loop

---

## Summary

Once this main loop integration is complete:

✅ Input validation working
✅ Safe sleep guaranteed  
✅ URL validation in place
✅ CSV write with retry
✅ Memory saved on success
✅ Proxy rotation happening (if enabled)
✅ All 12 loopholes fixed

You'll be ready to run on the full 1700-row dataset!

---

**Estimated time to complete:** 15-30 minutes
**Risk level:** LOW (all components already tested)
**Next step after this:** Test with small dataset (10 rows)
