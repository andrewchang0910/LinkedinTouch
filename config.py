import json
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
        "CMO",
        "Chief Marketing Officer",
        "Head of Growth",
        "Growth Manager",
        "Marketing Director",
        "BD Manager",
        "Business Development",
        "Head of Marketing",
        "Product Manager",
        "Co-Founder",
    ],
    "industry_keywords": [
        "crypto",
        "blockchain",
        "Web3",
        "DeFi",
        "NFT",
    ],
    "regions": [],
    # LinkedIn company size facets (used in URL params)
    # B=1-10, C=11-50, D=51-200, E=201-500, F=501-1000, G=1001-5000, H=5001-10000, I=10001+
    "company_sizes": ["B", "C", "D", "E"],
}

# Load campaign override from campaign.json if it exists (written by the web dashboard)
_CAMPAIGN_OVERRIDE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campaign.json")
if os.path.exists(_CAMPAIGN_OVERRIDE):
    with open(_CAMPAIGN_OVERRIDE, encoding="utf-8") as _f:
        CAMPAIGN.update(json.load(_f))

# Rate limits
DAILY_SCRAPE_CAP = 40
DAILY_MESSAGE_CAP = 20

# Paths
SESSION_FILE = "session.json"
DB_FILE = "linkedintouch.db"
LOG_FILE = "logs/activity.log"
ERROR_SCREENSHOT_DIR = "logs/errors"
