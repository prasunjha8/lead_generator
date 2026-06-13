"""
CSV loader with data validation and cleaning.
Handles messy real-world CSV data including multiline cells.
"""

import csv
import logging
import re
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

REQUIRED_COLS = ["Company Name"]

EXPECTED_COLS = [
    "Company Name", "POC", "E-Mail", "Phone No.", "Call Status",
    "Linkdlin", "Website", "Your Name", "Email Drafted",
    "Date contacted", "Mail Sent", "Reply received", "Follow up date", "UPDATE"
]


def _clean(val: str) -> str:
    """Strip whitespace and remove embedded newlines."""
    if not val:
        return ""
    return re.sub(r"\s+", " ", val.strip())


def _infer_website(company_name: str, website: str, email: str) -> str:
    website = website.strip()
    if website:
        return website

    # Try extracting domain from email
    email = email.strip()
    if email and "@" in email:
        domain = email.split("@")[-1].lower().strip()
        # Exclude generic/public email providers
        generic_providers = {
            "gmail.com", "yahoo.com", "yahoo.co.in", "yahoo.co.uk", "outlook.com",
            "hotmail.com", "rediffmail.com", "live.com", "aol.com", "zoho.com",
            "protonmail.com", "proton.me", "mail.com", "icloud.com", "gmx.com"
        }
        if domain not in generic_providers:
            return domain

    # If company name itself looks like a domain (e.g. Robu.in)
    cleaned_name = company_name.strip()
    if "." in cleaned_name and not cleaned_name.endswith("."):
        tlds = (".com", ".in", ".co.in", ".org", ".net", ".io", ".ai", ".co", ".tech", ".me", ".edu", ".ac.in")
        if cleaned_name.lower().endswith(tlds):
            return cleaned_name.lower()

    return ""


def load_companies(csv_path: Path) -> List[Dict[str, str]]:
    """
    Load and clean the sponsorship CSV.
    Returns a list of company dicts, skipping rows without a company name.
    """
    companies = []
    seen_keys: set = set()

    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)

        # Normalise headers (strip BOM / whitespace)
        reader.fieldnames = [h.strip() for h in (reader.fieldnames or [])]

        # Validate columns
        missing = [c for c in REQUIRED_COLS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"CSV is missing required columns: {missing}")

        for i, row in enumerate(reader, start=2):
            company_name = _clean(row.get("Company Name", ""))
            if not company_name:
                continue

            email_val = _clean(row.get("E-Mail", ""))
            website_val = _clean(row.get("Website", ""))
            inferred_website = _infer_website(company_name, website_val, email_val)

            record = {
                "Company Name": company_name,
                "POC":          _clean(row.get("POC", "")),
                "E-Mail":       email_val,
                "Phone No.":    _clean(row.get("Phone No.", "")),
                "Call Status":  _clean(row.get("Call Status", "")),
                "LinkedIn":     _clean(row.get("Linkdlin", "")),
                "Website":      inferred_website,
                "Your Name":    _clean(row.get("Your Name", "")),
                "_row":         i,
            }

            # De-duplicate: same company + same email
            dedup_key = f"{company_name.lower()}|{record['E-Mail'].lower()}"
            if dedup_key in seen_keys:
                logger.debug(f"Duplicate skipped (row {i}): {company_name}")
                continue
            seen_keys.add(dedup_key)

            companies.append(record)

    logger.info(f"Loaded {len(companies)} companies from {csv_path.name}")
    return companies
