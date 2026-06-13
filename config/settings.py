"""
Central configuration for Robolution Sponsorship Intelligence System.
All settings are loaded from environment variables with safe defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")


# ── API Keys ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY        = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY", "")

# ── Model preferences ─────────────────────────────────────────────────────────
GEMINI_MODEL        = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

GROQ_MODELS = [m.strip() for m in os.getenv(
    "GROQ_MODELS",
    "llama-3.3-70b-versatile,llama-3.1-8b-instant"
).split(",")]

OPENROUTER_MODELS = [m.strip() for m in os.getenv(
    "OPENROUTER_MODELS",
    "google/gemini-2.5-flash,meta-llama/llama-3.3-70b-instruct:free,deepseek/deepseek-r1:free"
).split(",")]

# ── Processing ────────────────────────────────────────────────────────────────
BATCH_SIZE          = int(os.getenv("BATCH_SIZE", "5"))
CHECKPOINT_EVERY    = int(os.getenv("CHECKPOINT_EVERY", "10"))
MAX_RETRIES         = int(os.getenv("MAX_RETRIES", "4"))
REQUEST_TIMEOUT     = int(os.getenv("REQUEST_TIMEOUT", "60"))
FORCE_REFRESH       = os.getenv("FORCE_REFRESH", "false").lower() == "true"

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR            = Path(__file__).parent.parent
INPUT_CSV           = BASE_DIR / "data" / "input.csv"
CACHE_DB            = BASE_DIR / os.getenv("CACHE_DB", "cache/research_cache.db")
OUTPUT_RESEARCH     = BASE_DIR / os.getenv("OUTPUT_RESEARCH", "output/companies_research.csv")
OUTPUT_OUTREACH     = BASE_DIR / os.getenv("OUTPUT_OUTREACH", "output/companies_outreach.csv")
LOG_FILE            = BASE_DIR / "logs" / "app.log"
CACHE_TTL_HOURS     = int(os.getenv("CACHE_TTL_HOURS", "720"))

# ── Club context (embedded for prompt injection) ───────────────────────────────
CLUB_CONTEXT = """
ORGANIZATION: Robolution (also known as Team Pratyunmis)
INSTITUTE: Birla Institute of Technology, Mesra (BIT Mesra)
FOUNDED: 2001
TYPE: Official robotics and innovation club

DOMAINS: Mechanical Design, Robotics, Electronics, Embedded Systems, 
         Programming, AI, Automation

ACHIEVEMENTS:
- Representative team for ABU ROBOCON
- Perfect score of 100 in 3D Design Analysis (2021)
- Workshops, technical outreach programs, and research projects
- Organizers of RoboSaga (flagship technology festival)
- Mentorship in robotics, AI, electronics, and software engineering

ROBOWARS JOURNEY:
- 2024: First-time participation in Robowars
- 2025: Qualified to Quarter Finals at national level
- 2026: Targeting significantly higher ranking, expanded participation,
        stronger industry partnerships, multi-institution competitions

SPONSORSHIP CAMPAIGN: Supporting Robowars team competitive development
and long-term club growth.
"""

# ── Sponsorship types catalog ──────────────────────────────────────────────────
SPONSORSHIP_TYPES = [
    "Monetary Sponsorship",
    "CNC Machining",
    "Milling",
    "Fabrication",
    "Laser Cutting",
    "Waterjet Cutting",
    "Sheet Metal Manufacturing",
    "3D Printing",
    "Electronics Components",
    "Sensors",
    "Motors",
    "Motor Controllers",
    "Batteries",
    "Embedded Hardware",
    "Software Licenses",
    "CAD Tools",
    "Simulation Tools",
    "AI Tools",
    "Cloud Credits",
    "Internship Opportunities",
    "Mentorship",
    "Technical Workshops",
    "Branding Partnerships",
    "Recruitment Opportunities",
]
