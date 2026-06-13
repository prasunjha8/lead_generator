"""
Discovery engine: automatically discovers new potential corporate sponsors for Robolution.
Uses LLM to suggest new companies in India, excluding already-targeted ones.
"""

import json
import logging
from typing import List, Dict, Optional

from src.llm_router import LLMRouter

logger = logging.getLogger(__name__)

DISCOVERY_PROMPT = """
You are a sponsorship research strategist helping Robolution, the official robotics club of BIT Mesra, India (representative team for ABU ROBOCON, Quarter Finals at national Robowars).
We need to discover new corporate sponsors in India.

EXCLUDE THE FOLLOWING COMPANIES (they are already in our list, DO NOT suggest them):
{existing_companies}

CATEGORIES TO SEARCH ACROSS:
1. Indian robotics component suppliers and retailers (motors, ESCs, sensors, batteries, controllers)
2. PCB manufacturing and assembly services in India
3. CNC machining, 3D printing, laser cutting, and sheet metal fabrication services in India
4. Motor and drive manufacturers (BLDC, servo, stepper) in India
5. Battery and power electronics companies in India
6. Embedded systems and microcontroller providers in India
7. Engineering software / CAD / simulation / AI tool providers with India offices
8. Industrial automation and PLCs with active India operations
9. EV, drone, UAV, defence-tech, and aerospace startups in India
10. Manufacturing/industrial PSUs near Jharkhand/West Bengal/Odisha

YOUR TASK:
Find {limit} new companies in India that are strong targets for Robolution.
{category_instruction}

Respond ONLY with a valid JSON object containing a list of companies under the "companies" key, containing no markdown, prose, or code fences.

JSON SCHEMA:
{{
  "companies": [
    {{
      "company_name": "Official company name",
      "website": "Company website domain or URL (use best search knowledge, e.g. company.com or company.in)",
      "industry": "Specific sector (e.g. PCB Manufacturing, EV Batteries, 3D Printing)"
    }}
  ]
}}
"""

async def discover_companies(
    llm: LLMRouter,
    limit: int = 10,
    category: Optional[str] = None,
    existing_companies: List[str] = None
) -> List[Dict[str, str]]:
    """
    Query the LLM to discover new sponsor targets.
    """
    existing_companies = existing_companies or []
    existing_str = ", ".join(existing_companies)

    if category:
        category_instruction = f"Focus exclusively on companies in the following category: {category}."
    else:
        category_instruction = "Select a diverse list of companies across the specified categories."

    prompt = DISCOVERY_PROMPT.format(
        limit=limit,
        existing_companies=existing_str,
        category_instruction=category_instruction
    )

    logger.info(f"Discovering {limit} new companies using LLM (Category: {category or 'General'})...")
    result = await llm.complete_json(prompt, max_tokens=4000)

    if not result or not isinstance(result, dict):
        logger.error("Failed to generate discovery list from LLM.")
        return []

    companies_list = result.get("companies", [])
    if not isinstance(companies_list, list):
        logger.error("Failed to parse companies list from JSON object.")
        return []

    # Normalise keys to match company schema
    discovered = []
    for item in companies_list:
        name = item.get("company_name", "").strip()
        website = item.get("website", "").strip()
        industry = item.get("industry", "").strip()
        if name:
            discovered.append({
                "Company Name": name,
                "Website": website,
                "Industry": industry,
                "POC": "Unknown",
                "E-Mail": "Missing",
                "Phone No.": "Missing",
                "LinkedIn": ""
            })

    logger.info(f"Successfully discovered {len(discovered)} new targets.")
    return discovered

