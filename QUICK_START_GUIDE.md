"""
QUICK_START_GUIDE.md
────────────────────
Guide to using rotating IP proxies and understanding loophole fixes.
"""

# 🚀 QUICK START - ROTATING IP PROXY SETUP

## Option 1: Start Simple (No Proxy)
```bash
# 1. Edit .env file
PROXY_SERVICE=none

# 2. Run script
python main.py

# Risk: May get rate-limited on large datasets
```

## Option 2: Bright Data (Recommended for 1000+ rows)
```bash
# 1. Sign up: https://brightdata.com/proxy-types/residential-proxies

# 2. Get your credentials:
#    - Username: Your account email
#    - Password: From dashboard
#    - Zone: From zone settings

# 3. Edit .env file:
PROXY_SERVICE=brightdata
BRIGHTDATA_USERNAME=youremail@example.com
BRIGHTDATA_PASSWORD=your-password-here
BRIGHTDATA_ZONE=your-zone-name

# 4. Run script
python main.py
```

## Option 3: Oxylabs (Good alternative)
```bash
# 1. Sign up: https://oxylabs.io/products/rotating-proxy

# 2. Get credentials from dashboard

# 3. Edit .env file:
PROXY_SERVICE=oxylabs
OXYLABS_USERNAME=your-username
OXYLABS_PASSWORD=your-password

# 4. Run script
python main.py
```

## Option 4: SmartProxy (Budget option)
```bash
# 1. Sign up: https://smartproxy.com

# 2. Get credentials

# 3. Edit .env file:
PROXY_SERVICE=smartproxy
SMARTPROXY_USERNAME=your-username
SMARTPROXY_PASSWORD=your-password

# 4. Run script
python main.py
```

---

# 🔍 LOOPHOLES FIXED

## Critical Fixes

### 1. **Input Validation**
   - ✓ Skips rows with empty/short names or companies
   - ✓ Prevents wasted API calls
   - ✓ Better error messages

**Before:**
```python
name = row.get("Name", "")
# Could be empty, causing search failures
```

**After:**
```python
is_valid, error = _validate_row_data(row_id, name, company, location, industry)
if not is_valid:
    logger.warning(f"Skip: {error}")
    continue
```

### 2. **Sleep Time Validation**
   - ✓ Ensures minimum 1-second sleep
   - ✓ Prevents negative sleep values
   - ✓ Consistent timing

**Before:**
```python
time.sleep(config.DELAY_SECONDS + random.uniform(-3, 5))
# Could be: 15 + (-3) = 12 seconds (ok)
# Or: 1 + (-3) = -2 seconds (BROKEN!)
```

**After:**
```python
def _safe_sleep(delay_seconds, jitter_range=(-3, 5)):
    jitter = random.uniform(*jitter_range)
    sleep_time = max(1, delay_seconds + jitter)  # Never negative
    time.sleep(sleep_time)
```

### 3. **Memory Saved on Error**
   - ✓ Query weights saved even on crash
   - ✓ Preserves learned patterns
   - ✓ Better resumption

**Before:**
```python
# Memory only saved inside if confidence >= threshold
# Lost on error or crash
```

**After:**
```python
except RateLimitException:
    save_memory(memory) # Save before waiting
    time.sleep(wait_sec)

except Exception:
    try:
        save_memory(memory) # Save on error too
    except:
        pass
```

### 4. **URL Validation**
   - ✓ LinkedIn URLs checked for format
   - ✓ Website URLs must start with http/https
   - ✓ Invalid URLs replaced with "Not Found"

**Before:**
```python
linkedin_url, ... = smart_linkedin_search(...)
# Could be garbage data
_append_row({..., "LinkedIn_URL": linkedin_url})
```

**After:**
```python
if not _validate_linkedin_url(linkedin_url):
    logger.warning(f"Invalid LinkedIn URL: {linkedin_url}")
    linkedin_url = "Not Found"

if not _validate_website_url(csv_website):
    logger.warning(f"Invalid website URL: {csv_website}")
    csv_website = "Not Found"
```

### 5. **CSV Write Retry Logic**
   - ✓ Retries on CSV write failure
   - ✓ Exponential backoff (1s, 2s, 4s)
   - ✓ Better error handling

**Before:**
```python
_append_row(row_data)
# Single attempt, could fail silently
```

**After:**
```python
if _append_row_safe(row_data, max_retries=3):
    stats.add_success(confidence)
else:
    stats.add_error()
    logger.error(f"Failed to write output row")
```

### 6. **Proxy Support**
   - ✓ Rotating IP per request
   - ✓ Fallback to direct connection
   - ✓ Retry on proxy failure

**New modules:**
- `enrichment/proxy_config.py` - Configuration
- `enrichment/proxy_manager.py` - Proxy rotation logic

### 7. **Query Validation**
   - ✓ Checks query length (3-500 chars)
   - ✓ Better error messages
   - ✓ Prevents malformed searches

### 8. **Timeout Handling**
   - ✓ Search timeout set to 30 seconds
   - ✓ Prevents infinite hangs
   - ✓ Treated as rate limit

### 9. **Result Validation**
   - ✓ Checks result format
   - ✓ Detects corrupted responses
   - ✓ Prevents downstream crashes

### 10. **Column Validation**
   - ✓ Checks column exists before access
   - ✓ Graceful handling of format changes
   - ✓ Skips missing columns

---

# 📊 PERFORMANCE RECOMMENDATIONS

### Small Datasets (< 1000 rows)
```env
PROXY_SERVICE=none
DELAY_SECONDS=15
BLOCK_WAIT_MINUTES=30
```
- Direct connection fine
- Estimated time: 4-6 hours

### Medium Datasets (1000-10000 rows)
```env
PROXY_SERVICE=smartproxy
DELAY_SECONDS=10
BLOCK_WAIT_MINUTES=15
```
- Rotating proxies help
- Estimated cost: $5-10/month (SmartProxy)
- Estimated time: 3-4 hours

### Large Datasets (> 10000 rows)
```env
PROXY_SERVICE=brightdata
DELAY_SECONDS=5
BLOCK_WAIT_MINUTES=10
```
- Best reliability
- Estimated cost: $20-50/month (Bright Data)
- Estimated time: 2-3 hours

---

# ✅ VERIFICATION CHECKLIST

Before running on large datasets:

- [ ] Test with 10-20 rows first
- [ ] Check enrichment.log for errors
- [ ] Verify output CSV format
- [ ] If rate limited, switch to proxy service
- [ ] Verify proxy credentials in .env
- [ ] Test proxy connectivity

---

# 🆘 TROUBLESHOOTING

### "Rate limited" errors
**Solution:** Switch from `PROXY_SERVICE=none` to `brightdata`, `oxylabs`, or `smartproxy`

### "Query too short" errors
**Solution:** Ensure input CSV has at least 3-character names and company names

### "Invalid LinkedIn URL" warnings
**Solution:** Normal - some searches don't find profiles, marked as "Not Found"

###  CSV write failures
**Solution:** Check disk space, check write permissions

### Proxy authentication errors
**Solution:** Verify credentials in .env file, check proxy service status

---

# 📈 THE NEW PROXY ROTATION FLOW

```
Row 1: Get IP A
       Search LinkedIn with IP A
       Search Website with IP A
       ↓
Row 2: Get IP B (different from A)
       Search LinkedIn with IP B
       Search Website with IP B
       ↓
Row 3: Get IP C (different from B)
       ... (continue rotating)
```

**Benefit:** Each row uses a fresh IP, dramatically reducing rate-limit risk

---

# 🔐 SECURITY NOTES

- **Never commit .env with credentials** (add to .gitignore)
- Credentials stored only locally in .env
- Proxy passwords are masked in logs
- All credentials transmitted securely

---

# 📞 SUPPORT RESOURCES

- **Bright Data:** https://brightdata.com/support
- **Oxylabs:** https://support.oxylabs.io
- **SmartProxy:** https://smartproxy.com/guide
- **DuckDuckGo Search:** https://www.duckduckgo.com/

---

Last updated: March 17, 2026
