"""
Research engine: gathers evidence then passes it to the LLM for analysis.
Never asks the LLM cold "what does company X do?" – gathers facts first.
"""

import asyncio
import logging
from typing import Dict, Optional

from src.llm_router import LLMRouter

from src.website_scraper import scrape_company_website, search_company_duckduckgo
from config.settings import CLUB_CONTEXT, SPONSORSHIP_TYPES

logger = logging.getLogger(__name__)


RESEARCH_PROMPT = """
You are a sponsorship research analyst for a student robotics club called Robolution at BIT Mesra, India.

{club_context}

TASK: Analyse the company below and generate a complete sponsorship intelligence report.

COMPANY INFORMATION:
Name: {company_name}
Website: {website}
LinkedIn: {linkedin}
Current POC: {current_poc}
Current Email: {current_email}
Current Phone: {current_phone}
Current LinkedIn: {current_linkedin}

GATHERED EVIDENCE:
{evidence}

SPONSORSHIP TYPES TO CONSIDER:
{sponsorship_types}

INSTRUCTIONS:
- Base your analysis on the gathered evidence and any current contact details.
- Find the best Point of Contact (POC) for sponsorship/partnerships (e.g. Marketing Manager, CSR Head, Brand Manager, Partnerships, Developer Relations, HR, CEO/Founder).
- If the current POC/email/phone from our sheet is correct, verify and keep it. If a better contact is found in the evidence, use the new contact.
- Estimate the contact confidence using the following rules:
  - HIGH: Email explicitly found in evidence (website/LinkedIn), or phone explicitly listed.
  - MEDIUM: Person verified but email is inferred from company domain email format (e.g., firstname.lastname@company.com).
  - LOW: Person likely exists but limited evidence.
  - Never present inferred emails as verified.
- Identify if they have any student/education programs, CSR programs, or sponsorship forms.
- Determine the Sponsorship Category: Monetary / Components / Fabrication / Electronics / Software / Cloud Credits / Mentorship / Recruitment.
- Determine the exact Suggested Ask (e.g., "INR 50,000 monetary sponsorship", "Free PCB manufacturing", "Free motors and ESCs", "Cloud credits", "CNC machining support", "Internship collaboration").
- Estimate the Response Likelihood: High / Medium / Low.
- Explain in 2-3 lines why this company is likely or unlikely to sponsor Robolution.

Respond with ONLY a valid JSON object — no markdown, no prose, no code fences.

JSON SCHEMA:
{{
  "company_summary": "2-3 sentence description of what the company does",
  "industry": "Primary industry sector",
  "products_services": "Key products and services offered",
  "company_size": "Startup / SME / Mid-size / Large / Enterprise",
  "target_market": "Who they sell to",
  "technologies_used": "Technologies/platforms they use or sell",
  "robotics_relevance_score": <integer 0-10>,
  "engineering_relevance_score": <integer 0-10>,
  "sponsorship_fit_score": <integer 0-100>,
  "potential_sponsorship_types": ["type1", "type2"],
  "potential_sponsorship_value": "Low (<50k INR) / Medium (50k-2L INR) / High (2L-10L INR) / Premium (10L+ INR)",
  "why_company_should_sponsor": "Specific reasons this company benefits from sponsoring Robolution",
  "why_robolution_is_relevant": "Specific reasons Robolution aligns with this company's goals",
  "how_company_can_help": "Concrete ways this company can support the team",
  "what_value_robolution_provides": "Tangible value Robolution gives back to the sponsor",
  "suggested_sponsorship_strategy": "Recommended approach for securing this sponsor",
  "suggested_talking_points": ["point1", "point2", "point3"],
  "csr_alignment": "How this sponsorship fits their CSR or education goals",
  "recruitment_angle": "Hiring/intern angle if relevant",
  "research_notes": "Key observations, caveats, data gaps",
  "confidence_score": <integer 0-100>,
  
  "poc_name": "Full name of the best point of contact found (or keep current)",
  "poc_title": "Designation/title of the contact",
  "poc_email": "Work email or inferred email. Write 'Unknown' if not found",
  "poc_phone": "Direct phone number if found, else 'Unknown'",
  "poc_linkedin": "LinkedIn profile URL of the contact if found, else 'Unknown'",
  "student_program": "Does this company have a known student/education program? e.g., 'Yes: offers free student licenses' or 'None'",
  "sponsorship_program": "Does this company have an active CSR or sponsorship email/form? e.g., 'Yes: CSR program' or 'None'",
  "sponsorship_category": "Monetary / Components / Fabrication / Electronics / Software / Cloud Credits / Mentorship / Recruitment",
  "suggested_ask": "Provide the exact sponsorship request we should make (e.g. 'INR 50,000 monetary sponsorship', 'Free PCB manufacturing')",
  "response_likelihood": "High / Medium / Low",
  "confidence": "High / Medium / Low",
  "notes": "Any other contact details or observations"
}}
"""


async def research_company(
    company: Dict[str, str],
    llm: LLMRouter
) -> Optional[Dict]:
    """
    Phase 1: Research a single company.
    1. Try to scrape website, general DDG search, and contact DDG search concurrently.
    2. Pass compiled evidence to LLM.
    """
    name             = company["Company Name"]
    website          = company.get("Website", "")
    linkedin         = company.get("LinkedIn", "")
    current_poc      = company.get("POC", "") or "Unknown"
    current_email    = company.get("E-Mail", "") or "Missing"
    current_phone    = company.get("Phone No.", "") or "Missing"
    current_linkedin = company.get("LinkedIn", "") or "Missing"

    # ── Step 1: gather evidence concurrently ─────────────────────────────────
    tasks = []
    
    # Task 0: scrape website if we have a URL
    if website:
        logger.info(f"  Scraping website: {website}")
        tasks.append(scrape_company_website(website))
    else:
        tasks.append(asyncio.sleep(0))
        
    # Task 1: general company search
    general_query = f"{name} company products services India robotics"
    if linkedin:
        general_query += f" {linkedin}"
    logger.info(f"  Searching DuckDuckGo for company info: {name}")
    tasks.append(search_company_duckduckgo(general_query))
    
    # Task 2: contact / POC / sponsorship search
    contact_query = f'"{name}" (sponsorship OR CSR OR "marketing manager" OR "partnerships" OR "university relations" OR contact) India'
    logger.info(f"  Searching DuckDuckGo for contacts: {name}")
    tasks.append(search_company_duckduckgo(contact_query))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    web_text = results[0] if not isinstance(results[0], Exception) and results[0] else ""
    general_search = results[1] if not isinstance(results[1], Exception) and results[1] else ""
    contact_search = results[2] if not isinstance(results[2], Exception) and results[2] else ""

    evidence_parts = []
    source = "knowledge_only"
    
    if web_text:
        evidence_parts.append(f"=== WEBSITE CONTENT ===\n{web_text}")
        source = "website_scraped"
    if general_search:
        evidence_parts.append(f"=== GENERAL SEARCH RESULTS ===\n{general_search}")
        if source == "knowledge_only":
            source = "ddg_search"
    if contact_search:
        evidence_parts.append(f"=== CONTACT/SPONSORSHIP SEARCH RESULTS ===\n{contact_search}")

    evidence = "\n\n".join(evidence_parts)
    if not evidence:
        evidence = f"No web content found. Company name: {name}"
        logger.warning(f"  No evidence gathered for: {name}")

    # ── Step 2: LLM analysis ─────────────────────────────────────────────────
    prompt = RESEARCH_PROMPT.format(
        club_context=CLUB_CONTEXT,
        company_name=name,
        website=website or "N/A",
        linkedin=linkedin or "N/A",
        current_poc=current_poc,
        current_email=current_email,
        current_phone=current_phone,
        current_linkedin=current_linkedin,
        evidence=evidence[:6000],
        sponsorship_types="\n".join(f"- {s}" for s in SPONSORSHIP_TYPES),
    )

    result = await llm.complete_json(prompt, max_tokens=8000)

    if not result:
        logger.error(f"  LLM returned no result for: {name}")
        return _fallback_result(name, website, source)

    result["research_source"] = source
    result["_company_name"]   = name
    result["website"]         = website
    result["linkedin"]        = linkedin
    return result


def _fallback_result(name: str, website: str, source: str) -> Dict:
    """Minimal result when LLM fails entirely."""
    return {
        "company_summary": "Research failed — manual review needed.",
        "industry": "Unknown",
        "products_services": "Unknown",
        "company_size": "Unknown",
        "target_market": "Unknown",
        "technologies_used": "Unknown",
        "robotics_relevance_score": 0,
        "engineering_relevance_score": 0,
        "sponsorship_fit_score": 0,
        "potential_sponsorship_types": [],
        "potential_sponsorship_value": "Unknown",
        "why_company_should_sponsor": "Manual research required.",
        "why_robolution_is_relevant": "Manual research required.",
        "how_company_can_help": "Manual research required.",
        "what_value_robolution_provides": "Manual research required.",
        "suggested_sponsorship_strategy": "Manual outreach required.",
        "suggested_talking_points": [],
        "csr_alignment": "Unknown",
        "recruitment_angle": "Unknown",
        "research_notes": "LLM analysis failed. No data available.",
        "confidence_score": 0,
        "research_source": source,
        "_company_name": name,
        "website": website,
        "linkedin": "",
        
        "poc_name": "Unknown",
        "poc_title": "Unknown",
        "poc_email": "Unknown",
        "poc_phone": "Unknown",
        "poc_linkedin": "Unknown",
        "student_program": "None",
        "sponsorship_program": "None",
        "sponsorship_category": "Monetary",
        "suggested_ask": "Monetary Support",
        "response_likelihood": "Low",
        "confidence": "Low",
        "notes": "Research failed.",
    }
