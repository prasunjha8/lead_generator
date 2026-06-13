# Robolution Sponsorship Intelligence System

Production-grade pipeline for automated sponsorship research and personalized outreach for **Robolution, BIT Mesra** (Team Pratyunmis).

---

## Motivation & Approach

### Why This System Was Created
When compiling sponsorship lists for the club, our junior members brought in a large master CSV of potential companies. However, many details (like official websites, correct emails, and LinkedIn handles) were missing or incomplete. 

Furthermore, drafting outreach emails was a huge bottleneck. While many people use AI to write emails nowadays, copy-pasting company names and details one-by-one is tedious, repetitive, and often results in generic, superficial AI-sounding drafts that corporate sponsors ignore.

We asked ourselves: **"Why not automate this entire pipeline at scale?"**
Instead of manually researching companies and writing cold emails one by one, we built this system to:
1. **Automate Contextual Research**: Perform deep, fact-based search engine queries and web scrapes first, and feed this real-time evidence to the LLM.
2. **Draft Personalized Outreach**: Automatically write highly customized emails referencing the company's specific product line, industry sector, and our Robowars timeline (2024 to 2026), making the email look genuinely tailored.
3. **Discover New Leads (Auto-Discovery)**: If we can automate research for existing list targets, we can also automate the discovery of *new* prospective sponsors in India (such as PCB vendors, CNC precision fabrication, EV motor manufacturers) and insert them straight into our pipeline.

Now, we have open-sourced this system so any teammate or junior can clone it, set up their own API keys, and run the pipeline to find and contact sponsors in minutes!

---


## What It Does

For every company in your CSV, the system:
1. **Scrapes** the company website (if available)
2. **Searches** DuckDuckGo as fallback
3. **Analyses** the company with an LLM (Gemini → Groq → OpenRouter, automatic failover)
4. **Scores** sponsorship fit (0–100, A+ to D priority)
5. **Generates** a highly personalized outreach email + follow-up
6. **Saves** everything to two output CSVs
7. **Updates the master input CSV** directly with lead contact details (POC, email, phone, website, LinkedIn)

All results are **cached in SQLite** — interrupted runs resume automatically, and re-running costs zero additional API calls.

---

## Folder Structure

```
robolution_sponsorship/
├── main.py                        ← Entry point
├── demo_dryrun.py                 ← Test without API keys
├── requirements.txt
├── .env                           ← Your API keys (never commit this)
├── .env.example                   ← Template
│
├── config/
│   └── settings.py                ← All configuration
│
├── src/
│   ├── csv_loader.py              ← Load & clean input CSV
│   ├── website_scraper.py         ← Async website + DuckDuckGo scraper
│   ├── llm_router.py              ← Gemini / Groq / OpenRouter with failover
│   ├── anthropic_provider.py      ← Optional Anthropic Claude provider
│   ├── research_engine.py         ← Company intelligence generation
│   ├── email_generator.py         ← Personalized email generation
│   ├── scoring_engine.py          ← Fit scoring & priority classification
│   ├── cache_manager.py           ← SQLite cache (80%+ API cost reduction)
│   ├── checkpoint_manager.py      ← Resume capability
│   ├── output_writer.py           ← CSV export
│   └── log_setup.py               ← Logging to file + console
│
├── data/
│   └── input.csv                  ← Your sponsorship CSV
│
├── output/                        ← Generated CSVs appear here
│   ├── companies_research.csv
│   └── companies_outreach.csv
│
├── cache/                         ← SQLite DB + checkpoints (auto-created)
│   ├── research_cache.db
│   └── checkpoint.json
│
└── logs/
    └── app.log                    ← Detailed processing log
```

---

## Installation

### 1. Clone / extract the project
```bash
cd robolution_sponsorship
```

### 2. Create a Python virtual environment (recommended)
```bash
python3 -m venv venv
source venv/bin/activate          # Linux / macOS
venv\Scripts\activate             # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

Full list:
```
aiohttp>=3.9.0
beautifulsoup4>=4.12.0
python-dotenv>=1.0.0
tqdm>=4.66.0
lxml>=5.0.0
```

### 4. Configure API keys

Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

Edit `.env`:
```env
GEMINI_API_KEY=your_gemini_key_here
GROQ_API_KEY=your_groq_key_here
OPENROUTER_API_KEY=your_openrouter_key_here
```

> The system works with **any single key**. All three give maximum resilience.

### 5. Place your input CSV
```
data/input.csv
```
The file must have at minimum a `Company Name` column. Your current CSV is already in the correct format.

---

## Usage

The system supports two workflow modes: **Enrichment Mode** and **Discovery Mode**.

### 1. Enrichment Mode (Default)
Finds and verifies contact details for companies already listed in the master CSV (`data/input.csv`). It will automatically populate missing fields or update them if a better lead is found.

```bash
# Run full enrichment (research + emails + updating master CSV)
python main.py

# Research only
python main.py --phase research

# Email generation only (re-generates emails from cached research)
python main.py --phase email

# Test on the first 10 companies
python main.py --limit 10
```

### 2. Discovery Mode (`--mode discover`)
Discovers completely new potential sponsors in India (across electronics, CNC, 3D printing, batteries, software, etc.), appends them to the master CSV (`data/input.csv`), and then automatically runs research and email generation for them.

```bash
# Discover 10 new sponsors and process them
python main.py --mode discover --discover-limit 10

# Discover 5 new sponsors specifically in the '3D Printing' category
python main.py --mode discover --discover-limit 5 --category "3D Printing"
```

### General Configuration Flags

```bash
# Force re-process everything (ignore cache)
python main.py --force-refresh

# Override concurrency (avoids rate limits, default: 5)
python main.py --batch-size 2

# Debug logging
python main.py --debug

# Test the pipeline without API keys (mock data)
python demo_dryrun.py
```

---

## Contact Confidence Rules

To prevent and track hallucinations, the pipeline classifies contact information into three categories in the output CSV files:
- **HIGH**: Contact info (email/phone/LinkedIn) was explicitly found in the website text or search snippets.
- **MEDIUM**: The person was verified to work at the company, but their work email format was inferred (e.g. `firstname.lastname@company.com`).
- **LOW**: The contact person likely exists, but has weak/unverified evidence.

You can filter your updated CSV by the `Confidence` column to prioritize high-confidence matches.

---

## Output Files

### `output/companies_research.csv`
| Column | Description |
|--------|-------------|
| Company Name | Cleaned company name |
| Industry | Primary sector |
| Products & Services | Key offerings |
| Company Summary | 2–3 sentence overview |
| Robotics Relevance Score | 0–10 |
| Engineering Relevance Score | 0–10 |
| Sponsorship Fit Score | 0–100 |
| Potential Sponsorship Type | e.g. Motors, Batteries, Cloud Credits |
| Potential Sponsorship Value | Potential tier (Low, Medium, High, Premium) |
| Why Company Should Sponsor Robolution | Specific business rationale |
| Why Robolution Is Relevant To Company | Alignment explanation |
| How Company Can Help Robolution | Concrete support options |
| What Value Robolution Provides | Sponsor benefits |
| Suggested Sponsorship Strategy | Strategy outline |
| Research Notes | Caveats, data gaps |
| Confidence Score | 0–100 |

### `output/companies_outreach.csv`
| Column | Description |
|--------|-------------|
| Company Name | |
| POC | Contact person |
| Email | Contact email |
| Phone | Contact phone |
| Email Subject | Ready-to-send subject line |
| Personalized Email | Full email body |
| Follow Up Email | Follow-up body |
| Sponsorship Fit Score | |
| Priority Category | A+ / A / B / C / D |

---

## Priority Scoring

| Score | Category | Meaning |
|-------|----------|---------|
| 90–100 | A+ | Highest Priority — contact immediately |
| 80–89 | A | Strong Prospect |
| 70–79 | B | Good Prospect |
| 60–69 | C | Moderate Prospect |
| < 60 | D | Low Priority |

---

## LLM Provider Setup

### Gemini (Primary — Free Tier)
1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Create API key
3. Set `GEMINI_API_KEY=...` in `.env`

**Model:** `gemini-2.5-flash` (fast, generous free tier)

### Groq (Fallback 1 — Free Tier)
1. Go to [console.groq.com](https://console.groq.com)
2. Create API key
3. Set `GROQ_API_KEY=...` in `.env`

**Models used:** `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`

### OpenRouter (Fallback 2 — Free Models)
1. Go to [openrouter.ai](https://openrouter.ai)
2. Create account and API key
3. Set `OPENROUTER_API_KEY=...` in `.env`

**Models used:** `google/gemini-2.5-flash:free`, `meta-llama/llama-3-8b-instruct:free`, `qwen/qwen-2.5-72b-instruct:free`

### Anthropic Claude (Optional)
Add `ANTHROPIC_API_KEY=...` to `.env` and modify `main.py` to include `AnthropicProvider`.

---

## Cost Optimization

The cache layer is aggressive by design:
- Every research result is stored in `cache/research_cache.db`
- Every email is stored in the same database
- Subsequent runs **skip all cached companies entirely**
- Only new companies consume API calls

**Expected API usage:**
- First run of 129 companies: ~129 research calls + ~129 email calls = ~258 total
- Second run (same companies): **0 API calls**
- Adding 20 new companies: **only 40 calls**

**Rate limit tips:**
```bash
# If hitting rate limits, reduce concurrency:
python main.py --batch-size 2

# Add delay between batches by setting a lower batch size
# The exponential backoff handles transient rate limits automatically
```

---

## Resume After Interruption

If the script is interrupted (Ctrl+C, network issue, power cut):
```bash
# Just re-run — it picks up exactly where it left off
python main.py
```

The checkpoint file at `cache/checkpoint.json` tracks every processed company.

---

## Logging

All activity is logged to `logs/app.log`:
```
2025-01-15 14:32:01 | INFO     | research_engine | [RESEARCH ] Processing: NVIDIA
2025-01-15 14:32:07 | INFO     | llm_router      | [Gemini] ✓ response received
2025-01-15 14:32:07 | INFO     | research_engine | [RESEARCH ] Done: NVIDIA (6.2s) score=88
2025-01-15 14:32:09 | INFO     | email_generator | [EMAIL GEN] Generating: NVIDIA
2025-01-15 14:32:14 | INFO     | llm_router      | [Gemini] ✓ response received
2025-01-15 14:32:14 | INFO     | cache_manager   | Cache SET (email): NVIDIA
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `No LLM provider configured` | Check `.env` has at least one valid API key |
| All providers failing | Check internet connection; try `--limit 1 --debug` |
| Rate limit errors | Reduce `--batch-size` to 1 or 2 |
| JSON parse errors | Normal occasionally — system retries automatically |
| Checkpoint not resuming | Check `cache/checkpoint.json` exists and is valid JSON |
| Empty research output | Run `python demo_dryrun.py` to verify pipeline, then check API keys |

---

## Architecture Notes

The pipeline is intentionally split into two independent phases:

**Phase 1 — Research** → scrape + LLM analysis → `companies_research.csv`  
**Phase 2 — Email** → LLM email generation → `companies_outreach.csv`

This means you can **regenerate emails with a different tone or template** without repeating any company research or spending additional API tokens on the intelligence phase.
