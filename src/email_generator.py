"""
Email generation engine.
Phase 2: Takes research output and generates highly personalized outreach emails.
Research and email generation are independent — emails can be regenerated without
repeating research.
"""

import logging
from typing import Dict, Optional

from src.llm_router import LLMRouter
from config.settings import CLUB_CONTEXT

logger = logging.getLogger(__name__)


EMAIL_PROMPT = """
You are writing sponsorship outreach emails for Robolution, the robotics club of BIT Mesra.

{club_context}

COMPANY PROFILE:
Company Name: {company_name}
Industry: {industry}
Products & Services: {products_services}
Company Summary: {company_summary}
Why They Should Sponsor: {why_sponsor}
How They Can Help: {how_help}
Potential Sponsorship Types: {sponsorship_types}
Talking Points: {talking_points}

CONTACT PERSON:
Name: {poc_name}
Email: {poc_email}

STRICT EMAIL REQUIREMENTS:
1. NEVER write a generic sponsorship email.
2. Mention the company's specific products/services/industry in the opening.
3. The email must feel like it was written specifically for THIS company.
4. Mention our Robowars journey: 2024 (first participation), 2025 (quarter-finals), 2026 (ambitious expansion).
5. Every email MUST include this exact sentence about the brochure:
   "To provide a detailed overview of our team, achievements, sponsorship opportunities, and visibility offerings, we have attached our sponsorship brochure for your reference."
6. Do NOT dump all club info into the email — let the brochure do the heavy lifting.
7. End with a specific call to action (meeting / call / email reply).

EMAIL TONE: Professional, student-led, confident, respectful, concise, industry-aware.
NOT sales-y or desperate.

PERSONALIZATION RULES:
- Manufacturing / CNC / Machining company → focus on fabrication, precision, engineering talent
- Electronics company → focus on components, motors, sensors, embedded systems
- Battery company → focus on power systems, energy, robotics applications
- Software / AI company → focus on AI, simulation, algorithms, autonomy
- Cloud company → focus on infrastructure, digital twins, training pipelines
- Automation / Robotics company → focus on shared vision, industry alignment
- Recruitment company → focus on talent pipeline, skilled engineers
- Startup → focus on brand visibility, student community, mutual growth

FOLLOW-UP EMAIL:
- Short (150-200 words)
- Reference the previous email
- Add one new value point
- Encourage a brief call or meeting

Respond ONLY with a valid JSON object — no markdown, no code fences.

{{
  "email_subject": "Subject line for the outreach email",
  "personalized_email": "Full email body (use \\n for line breaks)",
  "follow_up_email": "Full follow-up email body (use \\n for line breaks)",
  "follow_up_subject": "Subject line for follow-up"
}}
"""


async def generate_emails(
    company: Dict[str, str],
    research: Dict,
    llm: LLMRouter
) -> Optional[Dict]:
    """
    Generate personalized outreach + follow-up emails using research data.
    """
    name = company["Company Name"]

    # Resolve POC name using researched info with fallback to sheet POC
    poc_name = research.get("poc_name", "")
    if not poc_name or poc_name.lower().strip() in ("unknown", "none"):
        poc_raw = company.get("POC", "")
        poc_name = poc_raw.split("(")[0].strip() if poc_raw else "Team"
    else:
        # Extract first name / clean title suffix
        poc_name = poc_name.split("(")[0].split()[0].strip()

    if not poc_name:
        poc_name = "Team"

    poc_email = research.get("poc_email", "")
    if not poc_email or poc_email.lower().strip() in ("unknown", "none"):
        poc_email = company.get("E-Mail", "")

    prompt = EMAIL_PROMPT.format(
        club_context=CLUB_CONTEXT,
        company_name=name,
        industry=research.get("industry", ""),
        products_services=research.get("products_services", ""),
        company_summary=research.get("company_summary", ""),
        why_sponsor=research.get("why_company_should_sponsor", ""),
        how_help=research.get("how_company_can_help", ""),
        sponsorship_types=", ".join(research.get("potential_sponsorship_types", [])),
        talking_points=" | ".join(research.get("suggested_talking_points", [])),
        poc_name=poc_name,
        poc_email=poc_email,
    )

    result = await llm.complete_json(prompt, max_tokens=8000)

    if not result:
        logger.error(f"  Email generation failed for: {name}")
        return _fallback_email(name, poc_name)

    return result


def _fallback_email(company_name: str, poc_name: str) -> Dict:
    return {
        "email_subject": f"Sponsorship Opportunity — Robolution, BIT Mesra",
        "personalized_email": (
            f"Dear {poc_name},\n\n"
            f"I am reaching out from Robolution, the official robotics club of BIT Mesra. "
            f"We are seeking industry partners for our competitive robotics journey.\n\n"
            f"To provide a detailed overview of our team, achievements, sponsorship opportunities, "
            f"and visibility offerings, we have attached our sponsorship brochure for your reference.\n\n"
            f"We would love to explore a potential partnership with {company_name}.\n\n"
            f"Looking forward to your response.\n\nWarm regards,\nRobolution Team, BIT Mesra"
        ),
        "follow_up_email": (
            f"Dear {poc_name},\n\n"
            f"I wanted to follow up on our earlier email regarding a sponsorship partnership "
            f"with Robolution, BIT Mesra.\n\nWould you be available for a brief call to discuss "
            f"this further?\n\nThank you.\n\nWarm regards,\nRobolution Team"
        ),
        "follow_up_subject": "Following Up — Robolution Sponsorship | BIT Mesra",
    }
