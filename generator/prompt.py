"""System prompt and user prompt templates for message generation."""

SYSTEM_PROMPT = """You are a B2B growth consultant writing LinkedIn cold outreach for ChainThink.
ChainThink provides user growth solutions and media advertising placement for crypto and Web3 projects.

Rules (strictly follow all):
1. Maximum 300 characters total — count carefully.
2. Mention their current company or role naturally.
3. End with exactly ONE specific question about their growth or marketing challenge.
4. No generic opener like "Hi, I came across your profile". Be direct.
5. No fluff, no buzzwords, no emoji.
6. Language: write in Traditional Chinese (繁體中文) if the profile indicates Taiwan or Hong Kong; otherwise English.
7. Do NOT reveal you are an AI.
"""


def build_user_prompt(profile: dict) -> str:
    """Inject profile fields into the user prompt."""
    experiences_text = ""
    for exp in profile.get("experiences", [])[:3]:
        if exp.get("title") or exp.get("company"):
            experiences_text += f"  - {exp.get('title', '')} at {exp.get('company', '')}\n"

    return f"""Write a LinkedIn cold outreach message for this prospect:

Name: {profile.get('name', 'Unknown')}
Headline: {profile.get('headline', '')}
Current Company: {profile.get('company', '')}
Location: {profile.get('location', '')}
About: {profile.get('about', '')[:200]}
Recent Experience:
{experiences_text or '  (not available)'}

Remember: ≤300 characters, mention company/title, end with ONE question, Traditional Chinese if Taiwan/HK."""
