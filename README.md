# 📚 DATA ENRICHMENT PIPELINE - COMPLETE DOCUMENTATION

## Table of Contents
1. [The Problem & Solution](#the-problem--solution)
2. [System Overview](#system-overview)
3. [Architecture](#architecture)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Proxy System](#proxy-system)
7. [Loophole Fixes](#loophole-fixes)
8. [API Reference](#api-reference)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 The Problem & Solution

### **The Problem**

Imagine you have a spreadsheet with 1700 people's names and their companies:

| ID | Name | Company | Location |
|---|---|---|---|
| 1 | John Smith | Acme Corporation | London |
| 2 | Sarah Johnson | Tech Innovations | New York |
| 3 | Michael Brown | Green Energy Ltd | Singapore |

**But you need to find:**
- Their LinkedIn profile URLs (for recruitment, networking, or verification)
- Their company's official website (for research, email pattern matching, or sales)

**The Challenge:**
- ❌ You can't manually search 1700 people on LinkedIn - it would take weeks!
- ❌ You need automation - but reliable automation is hard
- ❌ Search engines rate-limit you if you search too fast
- ❌ You need to avoid being detected as a bot
- ❌ If the script crashes, you'd lose all your work

### **How This Program Solves It**

This program **automatically searches the web** for each person's LinkedIn profile and company website, and **adds the results back to your spreadsheet**:

| ID | Name | Company | LinkedIn_URL | Company_Website | Match_Quality |
|---|---|---|---|---|---|
| 1 | John Smith | Acme Corporation | `linkedin.com/in/john-smith-123` | `www.acme-corp.com` | 85% |
| 2 | Sarah Johnson | Tech Innovations | `linkedin.com/in/sarah-j-456` | `www.techinnovations.com` | 92% |
| 3 | Michael Brown | Green Energy Ltd | Not Found | `www.greenenergy.co.uk` | 45% |

**Here's how it works:**

1. **Reads your CSV** - Takes all 1700 rows with names and companies
2. **Validates data** - Skips rows with missing or invalid data (saves time)
3. **Searches automatically** - For each person, it searches:
   - DuckDuckGo for their LinkedIn profile
   - DuckDuckGo for their company website
4. **Uses smart timing** - Waits between searches so search engines don't block you
5. **Uses rotating IPs** (optional) - Changes IP addresses if needed to avoid detection
6. **Saves work safely** - If it crashes, it resumes from where it left off (no data lost)
7. **Shows results** - Adds LinkedIn URLs and websites back to your spreadsheet

### **Real Example**

**Before:**
```
Input: John Smith, Acme Corporation, London
```

**After (automated by this program):**
```
Output: John Smith, Acme Corporation, London
        → LinkedIn: https://linkedin.com/in/john-smith-acme
        → Website: https://www.acmecorp.com
        → Match Quality: 85%
```

### **Why This is Hard to Build (And Why We Fixed It)**

Building this sounds easy, but there are hidden problems:
- ❌ **Crash-safe saving** - Need to save results immediately or lose data
- ❌ **Rate limiting** - Search engines block you if you search too fast
- ❌ **Invalid data** - Some rows might have empty names (need to skip safely)
- ❌ **Bad URLs** - Need to validate that URLs are real LinkedIn profiles
- ❌ **Negative sleep time** - Random jitter could make timing negative
- ❌ **IP blocking** - One IP gets blocked quickly (need to rotate IPs)
- ❌ **Lost progress** - If memory crashes, learned query patterns are lost

**We fixed all 12 of these problems so you don't have to worry.**

---

## System Overview

**Purpose:** Enrich CSV data with LinkedIn profile URLs and company websites using web searches.

**Input:** CSV file with people data (name, company, location, etc.)
**Output:** Same data enriched with LinkedIn URLs and company websites

**Technology Stack:**
- Python 3.11
- pandas (CSV handling)
- ddgs (DuckDuckGo search)
- spacy (NLP for entity extraction)
- Rotating proxies (optional - Bright Data, Oxylabs, SmartProxy)

**Dataset Size:** Currently supports ~1700 rows (~4-6 hours with direct connection)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    main.py (Entry Point)                    │
│  - Load CSV / Validate rows / Process each person           │
│  - Orchestrate searches / Write output / Track progress     │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┼────────┐
    │        │        │
    ▼        ▼        ▼
┌────────┐ ┌────────┐ ┌──────────────┐
│linkedin│ │website │ │    search    │
│  .py   │ │  .py   │ │  (DDGS)      │
└────────┘ └────────┘ │   .py        │
    │        │        └────────┬─────┘
    │        │                 │
    └────────┼─────────────────┤
             │                 │
             ▼                 ▼
        ┌────────────────────────────┐
        │   proxy_manager.py         │
        │ (Rotate IPs per request)   │
        └────────────────────────────┘
```

**Module Responsibilities:**

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `main.py` | Orchestration & I/O | Load CSV, validate rows, write output, track progress |
| `search.py` | DuckDuckGo wrapper | Execute searches with retry, validate results, proxy support |
| `linkedin.py` | LinkedIn-specific search | Two-phase search with adaptive query weighting |
| `website.py` | Website finding | Ranked domain scoring for company websites |
| `proxy_manager.py` | IP rotation | Get next proxy, mark failed, service-specific URL building |
| `proxy_config.py` | Proxy credentials | Store proxy service settings and credentials |
| `config.py` | Settings | Centralized configuration from .env file |
| `memory.py` | Persistent state | Store query weights between runs |
| `utils.py` | Utilities | Text normalization, scoring, employment checks |
| `nlp_extractor.py` | Entity extraction | Extract locations, job titles from profiles |

---

## Installation

### 1. Clone repository
```bash
cd c:\Users\Touhid\GitHub\Data_mining_withpy
```

### 2. Create virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 4. Create .env file
```bash
cp .env.example .env
# Edit .env with your settings
```

### 5. Prepare input CSV
```
Place Split_Data_Part_1.csv in project root
Required columns: ID, Name, Position, Company, Industry, Location, Company Size, Category
```

### 6. Run script
```bash
python main.py
```

---

## Configuration

All settings stored in `.env` file (not included in git for security):

### Output Settings
```env
# Columns to include in output
OUTPUT_COLUMNS=ID,Name,Position,Company,Industry,Location,Company Size,Category,LinkedIn_URL,Job_Status,CSV_Website_Link,Current_Company,Current_Website_Link,Confidence_%

# Columns to exclude from input
EXCLUDED_COLUMNS=Price Range,Timeline,Review Summary,Rating,Review Date,Data Source
```

### Timing Settings
```env
# Delay between searches (seconds, with jitter)
DELAY_SECONDS=15

# Rate-limit wait time (minutes)
BLOCK_WAIT_MINUTES=30

# Search timeout (seconds)
SEARCH_TIMEOUT=30
```

### Search Behavior
```env
# LinkedIn search confidence threshold
MIN_CONFIDENCE_SCORE=60       # Percentage (0-100)

# LinkedIn search max iterations
LINKEDIN_MAX_ITERS=3

# Website search timeout
WEBSITE_SEARCH_TIMEOUT=20
```

### Proxy Configuration
```env
# Proxy service: none, brightdata, oxylabs, smartproxy, manual
PROXY_SERVICE=none

# Bright Data credentials
BRIGHTDATA_USERNAME=your-email@gmail.com
BRIGHTDATA_PASSWORD=your-password
BRIGHTDATA_ZONE=your-zone-name

# Oxylabs credentials
OXYLABS_USERNAME=your-username
OXYLABS_PASSWORD=your-password

# SmartProxy credentials
SMARTPROXY_USERNAME=your-username
SMARTPROXY_PASSWORD=your-password

# Proxy behavior
PROXY_TIMEOUT=15                    # Connection timeout (seconds)
PROXY_ROTATION_PER_ROW=true         # Rotate IP per row
PROXY_RETRY_COUNT=2                 # Retry attempts if proxy fails
PROXY_FALLBACK_TO_DIRECT=true       # Fall back to direct if all proxies fail
```

### Logging
```env
# Log file path
LOG_FILE=enrichment.log

# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
```

### File Paths
```env
# Input CSV
INPUT_FILE=Split_Data_Part_1.csv

# Output CSV
OUTPUT_FILE=Enriched_Data_Output_Ultimate.csv

# Memory file (for adaptive learning)
MEMORY_FILE=query_memory.json
```

---

## Proxy System

### How It Works

1. **Per-row rotation:** Each search request uses a different IP
2. **Fallback mechanism:** If proxy fails, automatically retry with direct connection
3. **Credential management:** All credentials in .env (never in code)
4. **Service abstraction:** Same code works with any supported proxy service

### Supported Services

#### Bright Data (Recommended)
- **Cost:** ~$20-50/month
- **URL Format:** `socks5://username-zone:password@proxy.brightdata.com:22225`
- **Performance:** Best reliability
- **Setup:** https://brightdata.com/proxy-types/residential-proxies

```env
PROXY_SERVICE=brightdata
BRIGHTDATA_USERNAME=your-email@gmail.com
BRIGHTDATA_PASSWORD=your-password
BRIGHTDATA_ZONE=your-zone-name
```

#### Oxylabs
- **Cost:** ~$15-40/month
- **URL Format:** `http://username:password@pr.oxylabs.io:7777`
- **Performance:** Good reliability
- **Setup:** https://oxylabs.io/products/rotating-proxy

```env
PROXY_SERVICE=oxylabs
OXYLABS_USERNAME=your-username
OXYLABS_PASSWORD=your-password
```

#### SmartProxy
- **Cost:** ~$8-25/month
- **URL Format:** `http://username:password@gate.smartproxy.com:7000`
- **Performance:** Good for budget-conscious
- **Setup:** https://smartproxy.com/guide

```env
PROXY_SERVICE=smartproxy
SMARTPROXY_USERNAME=your-username
SMARTPROXY_PASSWORD=your-password
```

#### Manual Proxies
```env
# Comma-separated list of proxy URLs
PROXY_SERVICE=manual
MANUAL_PROXIES=http://proxy1.com:8080,http://proxy2.com:8080,socks5://proxy3.com:1080
```

#### No Proxy (Direct Connection)
```env
PROXY_SERVICE=none
# Uses direct connection to DuckDuckGo
```

### Proxy Manager API

```python
from enrichment.proxy_manager import get_proxy_manager, get_next_proxy, mark_proxy_failed

# Get next proxy (or None if PROXY_SERVICE=none)
proxy = get_next_proxy()
# Returns: {"http": "http://...", "https": "http://..."} or None

# Mark proxy as failed (won't be used for rest of session)
mark_proxy_failed(proxy)

# Reset manager for new session
proxy_manager = get_proxy_manager(reset=True)
```

### Proxy Flow Example

```python
# search.py: _fetch() function
def _fetch(query: str, max_results: int = 10):
    proxy = get_next_proxy()  # Get rotation IP
    try:
        with DDGS(proxy=proxy_dict, timeout=SEARCH_TIMEOUT) as ddgs:
            results = ddgs.text(query, max_results=max_results)
    except RateLimitException:
        raise  # Re-raise immediately
    except ProxyError:
        mark_proxy_failed(proxy)  # Mark this proxy as failed
        if PROXY_FALLBACK_TO_DIRECT:
            # Retry without proxy
            results = _fetch_direct(query, max_results)
    return results
```

---

## Loophole Fixes

### Summary Table

| # | Issue | Impact | Fix | Severity |
|---|-------|--------|-----|----------|
| 1 | No input validation | Crashes on empty names | Skip invalid rows | HIGH |
| 2 | Negative sleep time | Unpredictable timing | Ensure min 1 second | CRITICAL |
| 3 | Memory not saved | Loss of learned patterns | Save before wait | MEDIUM |
| 4 | No URL validation | Invalid data in output | Validate URL format | HIGH |
| 5 | CSV write not retried | Data loss on I/O error | Retry with backoff | CRITICAL |
| 6 | No column validation | KeyError on format change | Check existence | MEDIUM |
| 7 | No proxy support | Rate-limited on large datasets | Full proxy system | HIGH |
| 8 | No timeout on searches | Infinite hangs | 30-second timeout | CRITICAL |
| 9 | No query validation | Malformed search requests | Validate 3-500 chars | MEDIUM |
| 10 | No result validation | Corrupted data crashes | Format checking | MEDIUM |
| 11 | Non-absolute log path | Logging to wrong location | Use config path | LOW |
| 12 | No proxy fallback | Total failure if proxy dies | Fallback to direct | HIGH |

### Detailed Fixes

#### Fix #1: Input Validation
```python
def _validate_row_data(row_id: str, name: str, company: str, 
                       location: str, industry: str) -> tuple[bool, str]:
    """Validate minimum required fields exist."""
    if not name or len(name.strip()) < 2:
        return False, f"ID {row_id}: Name too short or empty"
    if not company or len(company.strip()) < 2:
        return False, f"ID {row_id}: Company too short or empty"
    return True, ""

# Usage in main loop:
is_valid, error = _validate_row_data(row_id, name, company, location, industry)
if not is_valid:
    logger.warning(f"Skip: {error}")
    continue
```

#### Fix #2: Safe Sleep with Min Guarantee
```python
def _safe_sleep(delay_seconds: int, jitter_range: tuple = (-3, 5)):
    """Sleep for specified seconds with jitter, minimum 1 second."""
    if delay_seconds < 0:
        delay_seconds = 1
    min_jitter, max_jitter = jitter_range
    jitter = random.uniform(min_jitter, max_jitter)
    sleep_time = max(1, delay_seconds + jitter)  # Never sleep < 1 second
    time.sleep(sleep_time)

# Usage:
_safe_sleep(config.DELAY_SECONDS)  # Always >= 1 second
```

#### Fix #3: Memory Saved Before Rate-Limit Wait
```python
except RateLimitException as exc:
    logger.warning(f"Rate limited. Waiting {wait_minutes} minutes...")
    memory.save()  # CRITICAL: Save before waiting
    time.sleep(wait_seconds)
    continue
```

#### Fix #4: URL Validation
```python
def _validate_linkedin_url(url: str) -> bool:
    """Check if URL is valid LinkedIn profile or 'Not Found'."""
    if url == "Not Found":
        return True
    return url.startswith("http") and "linkedin.com/in/" in url

def _validate_website_url(url: str) -> bool:
    """Check if URL is valid website or 'Not Found'."""
    if url == "Not Found":
        return True
    return url.startswith(("http://", "https://"))

# Usage:
if not _validate_linkedin_url(linkedin_url):
    linkedin_url = "Not Found"
```

#### Fix #5: CSV Write with Retry Logic
```python
def _append_row_safe(row_data: dict, max_retries: int = 3) -> bool:
    """Append row to CSV with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            _append_row(row_data)
            return True
        except Exception as exc:
            if attempt < max_retries - 1:
                backoff = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"CSV write failed (attempt {attempt+1}/{max_retries}), "
                             f"retrying in {backoff}s...")
                time.sleep(backoff)
            else:
                logger.error(f"CSV write failed after {max_retries} attempts")
                return False
    return False
```

---

## API Reference

### search.py

```python
from enrichment.search import get_search_results

# Main function
results = get_search_results(
    query: str,              # Search query (3-500 chars)
    max_results: int = 10   # Max results to return
) -> list[dict]
# Returns: [{"href": "url", "title": "...", "body": "..."}, ...]
# Raises: RateLimitException if rate limited
```

### linkedin.py

```python
from enrichment.linkedin import smart_linkedin_search

linkedin_url, snippet, job_status, confidence = smart_linkedin_search(
    name: str,                # Person's name
    company: str,             # Current/previous company
    location: str,            # Location
    industry: str,            # Industry
    memory: dict              # Query memory (for adaptive learning)
)
# Returns: (url, snippet, job_status, confidence_percent)
```

### website.py

```python
from enrichment.website import find_company_website

website_url, domain = find_company_website(
    company: str,            # Company name
    industry: str = ""       # Industry (optional)
)
# Returns: (website_url, domain_name)
```

### proxy_manager.py

```python
from enrichment.proxy_manager import (
    get_proxy_manager,
    get_next_proxy,
    mark_proxy_failed
)

# Get next proxy in rotation
proxy_dict = get_next_proxy()
# Returns: {"http": "http://...", "https": "http://..."} or None

# Mark proxy as failed (session-wide)
mark_proxy_failed(proxy_dict)

# Get proxy manager directly
manager = get_proxy_manager(reset=False)
```

---

## Troubleshooting

### Issue: "Rate limited" errors after 500-1000 rows

**Root Cause:** DuckDuckGo is rate-limiting IP address

**Solution 1 (Quick):**
```env
DELAY_SECONDS=30  # Increase delay between requests
```

**Solution 2 (Recommended):**
```env
PROXY_SERVICE=brightdata  # Switch to rotating proxies
# Add credentials...
```

### Issue: "Query too short" or "Query too long" errors

**Root Cause:** Search queries must be 3-500 characters

**Solution:** Check input CSV has valid company names and locations

### Issue: "Invalid LinkedIn URL" warnings appearing frequently

**This is normal.** Some searches legitimately don't find profiles.
- Good hit rate is 60-70%
- "Not Found" is valid output

### Issue: Proxy authentication failed

**Root Cause:** Credentials in .env are wrong

**Solution:**
1. Verify credentials in proxy service dashboard
2. Double-check .env file (no typos)
3. Test proxy connectivity: `curl -x [proxy_url] https://www.google.com`

### Issue: CSV write failures

**Root Cause:** Disk full, permission error, or file locked

**Solution:**
1. Check disk space: `dir c:\` (Windows)
2. Check file permissions: Right-click `Enriched_Data_Output_Ultimate.csv` → Properties
3. Ensure file not open in Excel/other app
4. Script will retry 3 times automatically

### Issue: Script hangs indefinitely

**Root Cause:** Search took too long or proxy is stuck

**Solution:** 
- Wait 30 seconds (timeout)
- Or Ctrl+C and run again
- Memory is saved, resumes from next row

### Issue: "ModuleNotFoundError: enrichment"

**Root Cause:** Wrong working directory

**Solution:**
```bash
cd c:\Users\Touhid\GitHub\Data_mining_withpy
python main.py  # NOT python enrichment/main.py
```

---

## Performance Tuning

### For Speed:
```env
DELAY_SECONDS=5              # Faster searches
PROXY_SERVICE=brightdata     # Rotate IPs quickly
BLOCK_WAIT_MINUTES=5         # Shorter rate-limit wait
```
Estimated: 2-3 hours for 1700 rows

### For Safety:
```env
DELAY_SECONDS=30            # Slower, less noticeable
PROXY_SERVICE=none          # Direct (if small dataset)
BLOCK_WAIT_MINUTES=60       # Respect rate limits
```
Estimated: 6-8 hours for 1700 rows

### Balanced:
```env
DELAY_SECONDS=15            # Medium speed
PROXY_SERVICE=smartproxy    # Cheap proxies
BLOCK_WAIT_MINUTES=30       # Reasonable wait
```
Estimated: 4-5 hours for 1700 rows

---

## Resources

- **DuckDuckGo:** https://www.duckduckgo.com/
- **Bright Data:** https://brightdata.com/proxy-types/residential-proxies
- **Oxylabs:** https://oxylabs.io/products/rotating-proxy
- **SmartProxy:** https://smartproxy.com/

---

**Document Version:** 1.0
**Last Updated:** March 17, 2026
**Maintained By:** Data Mining Team
