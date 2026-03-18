import os
from dotenv import load_dotenv

load_dotenv()

# LinkedIn credentials
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Campaign filters — edit these for each campaign
CAMPAIGN = {
    "job_titles": [
        "HR Manager",
        "Talent Acquisition",
        "Recruiter",
    ],
    "industries": [
        "Technology",
        "Financial Services",
    ],
    "regions": [
        "Taiwan",
        "Hong Kong",
    ],
    # LinkedIn company size facets (used in URL params)
    # B=1-10, C=11-50, D=51-200, E=201-500, F=501-1000, G=1001-5000, H=5001-10000, I=10001+
    "company_sizes": ["C", "D", "E", "F"],
    "company_size_min": 11,
    "company_size_max": 1000,
}

# Rate limits
DAILY_SCRAPE_CAP = 40
DAILY_MESSAGE_CAP = 20

# Paths
SESSION_FILE = "session.json"
DB_FILE = "linkedintouch.db"
LOG_FILE = "logs/activity.log"
ERROR_SCREENSHOT_DIR = "logs/errors"
