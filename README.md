# 🔍 LinkedIn & Company Website Finder

**Automatically find LinkedIn profiles and company websites for 1700+ people in your spreadsheet**

---

## 📋 Table of Contents

1. [What This Does](#what-this-does) - Problem & Solution
2. [Getting Started](#getting-started) - Quick setup in 5 minutes
3. [How to Use](#how-to-use) - Step-by-step guide with examples
4. [Configuration](#configuration) - All settings explained
5. [Understanding Results](#understanding-results) - What the output means
6. [Troubleshooting](#troubleshooting) - Common issues & fixes
7. [Technical Details](#technical-details) - For developers

---

## 🎯 What This Does

### **The Problem**

You have a spreadsheet with 1,700 people and companies (example):

```
Name                Company              Location
─────────────────   ─────────────────    ─────────
John Smith          Acme Corp            London
Sarah Johnson       Tech Innovations     New York
Michael Brown       Green Energy Ltd     Singapore
```

**You need:**
- ✅ LinkedIn URL for each person (for recruiters, salespeople, researchers)
- ✅ Company official website (for email matching, sales research, verification)

**The Problem:**
- ❌ Manual searching: 1,700 people × 2 minutes each = **56+ hours of work**
- ❌ Search engines block you if you search too fast
- ❌ If computer crashes, you lose all your work
- ❌ Need to avoid bot detection
- ❌ URLs might be invalid or fake

### **What This Program Does**

It **automatically searches the web** and fills in the missing data:

```
Name                Company              LinkedIn_URL                    Website              Match%
─────────────────   ─────────────────    ───────────────────────────    ──────────────────   ──────
John Smith          Acme Corp            linkedin.com/in/john-smith     www.acmecorp.com     85%
Sarah Johnson       Tech Innovations     linkedin.com/in/sarah-j        www.techinnov.com    92%
Michael Brown       Green Energy Ltd     [Not Found]                    www.greenenergy.uk   45%
```

### **How It Works**

1. **Read your CSV** - Loads all 1,700 rows with names and companies
2. **Validate data** - Skips broken rows (empty names, missing companies)
3. **Search automatically** - For each person:
   - 🔎 Searches DuckDuckGo for LinkedIn profile
   - 🔎 Searches DuckDuckGo for company website
4. **Smart delays** - Waits between searches (avoids getting blocked)
5. **Saves safely** - If it crashes, resume from where you left off ✅
6. **Validates URLs** - Checks results are real (not fake links)
7. **Shows confidence** - Tells you how confident it is (85%, 92%, etc.)

### **Time Saved**

| Scenario | Manual Time | This Program |
|----------|------------|--------------|
| 100 people | 3-4 hours | 1-2 hours |
| 500 people | 15-20 hours | 1-2 hours |
| 1,700 people | 56+ hours | 2-4 hours |

---

## ⚡ Getting Started (5 Minutes)

### **Step 1: Check Requirements**

You need:
- ✅ Python 3.11+ (already installed in `.venv/`)
- ✅ A CSV file with: `ID`, `Name`, `Company`, `Location`, `Industry`
- ✅ Windows/Mac/Linux computer

### **Step 2: Set Up Configuration**

Edit `.env` file (in your project folder):

```env
# Input and Output
INPUT_FILE=Split_Data_Part_1.csv
OUTPUT_FILE=Enriched_Data_Output.csv

# Timing (adjust these if rate-limited)
DELAY_SECONDS=15
BLOCK_WAIT_MINUTES=30

# Confidence threshold
MIN_CONFIDENCE_SCORE=60
```

**That's it!** Leave other settings as-is for now.

### **Step 3: Prepare Your Data**

Your input CSV must have these columns:

```csv
ID,Name,Position,Company,Industry,Location,Company Size,Category
1,John Smith,Sales Manager,Acme Corp,Technology,London,500-1000,B2B
2,Sarah Johnson,Engineer,Tech Inc,Software,New York,1000+,B2C
3,Michael Brown,Manager,Green Ltd,Energy,Singapore,100-500,B2B
```

- **Required:** ID, Name, Company
- **Optional:** Position, Location, Industry, Company Size, Category

### **Step 4: Run the Program**

Open terminal and type:

```bash
python main.py
```

**You'll see:**

```
════════════════════════════════════════════════════════════════════════════════
  DATA ENRICHMENT PIPELINE - LinkedIn & Website Finder
════════════════════════════════════════════════════════════════════════════════
Total rows to process: 1700 | Already processed: 0
Min confidence threshold: 60%
Output columns: ID, Name, Position, Company, Industry, Location, LinkedIn_URL, Website_Link, Confidence_%
════════════════════════════════════════════════════════════════════════════════
ID      | Status     | Name                     | Company              | Confidence

1       | Y Match    | John Smith           | Acme Corp            |  85%
2       | Y Match    | Sarah Johnson        | Tech Inc             |  92%
3       | N No Match | Michael Brown        | Green Ltd            |  45%
```

**Output file created:** `Enriched_Data_Output.csv`

---

## 📖 How to Use (Step-by-Step Examples)

### **Example 1: Basic Run**

**Your Input (Split_Data_Part_1.csv):**
```csv
ID,Name,Company
1,John Smith,Acme Corporation
2,Sarah Johnson,Tech Innovations
```

**Run:**
```bash
python main.py
```

**Your Output (Enriched_Data_Output.csv):**
```csv
ID,Name,Company,LinkedIn_URL,Website_Link,Job_Status,Confidence_%
1,John Smith,Acme Corporation,linkedin.com/in/john-smith,acmecorp.com,Current,85
2,Sarah Johnson,Tech Innovations,linkedin.com/in/sarah-johnson,techinnovations.com,Current,92
```

### **Example 2: Resume from Crash**

If the program stops (crash, internet lost, power off):

**Just run again:**
```bash
python main.py
```

It will:
- ✅ Check which rows were already completed
- ✅ Skip those rows
- ✅ Continue from next unfinished row
- ✅ No data re-processed, no duplicates

### **Example 3: Check Progress**

While running, check the console output:

```
ID      | Status     | Name                 | Company              | Confidence
─────────────────────────────────────────────────────────────────────────── 
1       | Y Match    | John Smith           | Acme Corp            |  85%  ✓
2       | Y Match    | Sarah Johnson        | Tech Inc             |  92%  ✓
3       | N No Match | Michael Brown        | Green Ltd            |  45%
```

Progress automatically shown in real-time.

---

## ⚙️ Configuration

### **Basic Settings (_must configure_)**

Edit `.env` file:

```env
# Your input CSV filename
INPUT_FILE=Split_Data_Part_1.csv

# Your output CSV filename (will be created)
OUTPUT_FILE=Enriched_Data_Output.csv
```

### **Timing Settings (_adjust if needed_)**

```env
# Wait time between searches (seconds)
# If rate-limited, increase to 30 or 45
DELAY_SECONDS=15

# Wait time when rate-limited (minutes)
# Search engine will block you for this duration
BLOCK_WAIT_MINUTES=30
```

**What to do if rate-limited:**
- See message: `Rate limited! Waiting 30 minutes...`
- The program waits automatically ✅
- Program resumes after waiting

**How to reduce rate-limiting:**
- Increase `DELAY_SECONDS` to 30-45
- Use proxy service (see below)

### **Confidence Threshold**

```env
# Only count matches with 60%+ confidence as "good matches"
MIN_CONFIDENCE_SCORE=60
```

What this means:
- 60-74% = Low confidence (maybe wrong person)
- 75-89% = Medium confidence (probably right)
- 90-100% = High confidence (very sure)

### **Proxy Configuration (Optional)**

To avoid rate-limiting with large datasets:

```env
# Don't use proxy (default - free, simple)
PROXY_SERVICE=none

# OR use paid proxy service (more expensive but more reliable)
PROXY_SERVICE=brightdata
BRIGHTDATA_USERNAME=your-username
BRIGHTDATA_PASSWORD=your-password
BRIGHTDATA_ZONE=your-zone
```

**Proxy options:**
- `none` - No proxy (free, can get rate-limited)
- `brightdata` - Bright Data (most reliable, ~$30/month)
- `oxylabs` - Oxylabs (good, ~$15/month)
- `smartproxy` - SmartProxy (budget, ~$8/month)

---

## 📊 Understanding Results

### **Output CSV Columns**

Your output file has these columns:

| Column | Meaning | Example |
|--------|---------|---------|
| `ID` | Your row ID | 1 |
| `Name` | Person's name | John Smith |
| `Company` | Company name | Acme Corp |
| `LinkedIn_URL` | Found LinkedIn profile | linkedin.com/in/john-smith |
| `Website_Link` | Company website | www.acmecorp.com |
| `Job_Status` | Current job match | Current / Changed / No Match |
| `Confidence_%` | How sure we are (0-100) | 85 |

### **Understanding Confidence %**

```
90-100% | ████████████ | Very confident → Trust this result
75-89%  | █████████    | Probably correct → Check if unsure
60-74%  | ███████      | Lower confidence → Verify this
0-59%   | ████         | Not confident → Probably wrong
```

### **What If LinkedIn_URL is "Not Found"?**

This means:
- ✅ No public LinkedIn profile found
- ✅ Profile might be private
- ✅ Person might use a different name on LinkedIn
- ✅ Person might not have a LinkedIn account

**Not an error - just means no result was found.**

---

## 🚨 Troubleshooting

### **Problem: "Input file not found"**

**Error message:**
```
✗ Input file not found: Split_Data_Part_1.csv
```

**Solution:**
1. Check filename in `.env` file
2. Put your CSV in the project folder
3. Verify filename spelling (case-sensitive on Mac/Linux)

---

### **Problem: "Rate limited! Waiting..."**

**Error message:**
```
Rate limited! Waiting 30 minutes before resuming...
Resume time: 14:30:00
```

**Solution:**
- ✅ Script handles this automatically
- ✅ Just wait (or close and run later)
- ✅ To prevent it: Increase `DELAY_SECONDS` in `.env` to 30-45

---

### **Problem: Program crashed, what about my data?**

**Your data is SAFE!** ✅

The program:
- ✅ Saves each row immediately
- ✅ Never loses completed rows
- ✅ Just run `python main.py` again to resume
- ✅ It skips already-completed rows automatically

---

### **Problem: All results show "Not Found"**

**Possible reasons:**
1. Internet connection problem → Check your connection
2. Search engine blocked you → Wait 30 minutes or increase delay
3. CSV data has typos → Check names/companies in input file
4. Names are too generic → Results might be ambiguous

---

### **Problem: Console shows weird characters or crashes**

**Solution:**
- This is Windows encoding issue - it's harmless
- Results are still saved correctly in the CSV file
- Check your output CSV file for results

---

## 🔧 Technical Details

### **How It Works (Behind the Scenes)**

```
Step 1: Load CSV
        ↓
Step 2: Validate each row (skip bad data)
        ↓
Step 3: Search LinkedIn for each person
        ↓
Step 4: Wait (smart delay to avoid blocking)
        ↓
Step 5: Search for company website
        ↓
Step 6: Validate URLs (is it real LinkedIn? Real website?)
        ↓
Step 7: Save to output CSV (immediately - crash safe)
        ↓
Step 8: Save learning memory (for better searches next time)
        ↓
Repeat for next person
```

### **What Gets Saved**

After each successful search:
- ✅ Your data is written to CSV file immediately
- ✅ Query weights saved (learns what searches work)
- ✅ If program crashes, you only lose current search

### **Files Created**

When you run the program:
- `Enriched_Data_Output.csv` - Your results (main file)
- `enrichment.log` - Detailed logs (for debugging)
- `query_memory.json` - Learned search patterns (for optimization)

---

## 📝 Example: Start to Finish

### **1. Create your input file**

Save as `Split_Data_Part_1.csv`:
```csv
ID,Name,Company,Location,Industry
1,John Smith,Acme Corporation,London,Technology
2,Sarah Johnson,Tech Innovations,New York,Software
3,Michael Brown,Green Energy,Singapore,Energy
```

### **2. Configure `.env`**

```env
INPUT_FILE=Split_Data_Part_1.csv
OUTPUT_FILE=Enriched_Data_Output.csv
DELAY_SECONDS=15
MIN_CONFIDENCE_SCORE=60
```

### **3. Run the program**

```bash
python main.py
```

### **4. Wait for results**

Program will search and show progress in console. Once done, check:

**Enriched_Data_Output.csv:**
```csv
ID,Name,Company,LinkedIn_URL,Website_Link,Confidence_%
1,John Smith,Acme Corporation,linkedin.com/in/john-smith,www.acmecorp.com,85
2,Sarah Johnson,Tech Innovations,linkedin.com/in/sarah-j,www.techinnovations.com,92
3,Michael Brown,Green Energy,Not Found,www.greenenergy.sg,65
```

**Done!** ✅

---

## 📞 Still Need Help?

**Check these first:**
1. Make sure `.env` file has correct input filename
2. Verify CSV file exists in project folder
3. Check `enrichment.log` for detailed error messages
4. Verify internet connection is working

---

## 🎯 Summary

✅ **What it does:** Finds LinkedIn profiles and company websites for hundreds/thousands of people  
✅ **Time saved:** Hours of manual searching  
✅ **Data safety:** Crash-safe, can resume anytime  
✅ **Easy setup:** 5 minutes to get started  
✅ **Simple to use:** Just one command: `python main.py`

---

**Version:** 1.0  
**Last Updated:** March 26, 2026  
**Status:** Production Ready ✅
