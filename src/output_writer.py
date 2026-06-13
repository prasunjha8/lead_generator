"""
CSV output writer.
Produces two output files:
  research_output.csv  — company intelligence
  outreach_output.csv  — personalized emails
"""

import csv
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

RESEARCH_COLS = [
    "Company Name",
    "Website",
    "LinkedIn",
    "Industry",
    "Company Summary",
    "POC Name",
    "POC Title",
    "POC Email",
    "POC Phone",
    "POC LinkedIn",
    "Student Program",
    "Sponsorship Program",
    "Sponsorship Category",
    "Suggested Ask",
    "Sponsorship Fit Score",
    "Response Likelihood",
    "Confidence",
    "Notes",
]

OUTREACH_COLS = [
    "Company Name",
    "POC",
    "Email",
    "Phone",
    "Email Subject",
    "Personalized Email",
    "Follow Up Email",
    "Sponsorship Fit Score",
    "Priority Category",
]


def _safe(val) -> str:
    if isinstance(val, list):
        return " | ".join(str(v) for v in val)
    return str(val) if val is not None else ""


def write_research_csv(rows: List[Dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=RESEARCH_COLS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            email = _safe(row.get("poc_email")).strip().lower()
            if not email or email in ("unknown", "none", "missing", ""):
                continue
            writer.writerow({
                "Company Name":          _safe(row.get("_company_name") or row.get("company_name")),
                "Website":               _safe(row.get("website")),
                "LinkedIn":              _safe(row.get("linkedin")),
                "Industry":              _safe(row.get("industry")),
                "Company Summary":        _safe(row.get("company_summary")),
                "POC Name":              _safe(row.get("poc_name")),
                "POC Title":             _safe(row.get("poc_title")),
                "POC Email":             _safe(row.get("poc_email")),
                "POC Phone":             _safe(row.get("poc_phone")),
                "POC LinkedIn":          _safe(row.get("poc_linkedin")),
                "Student Program":       _safe(row.get("student_program")),
                "Sponsorship Program":   _safe(row.get("sponsorship_program")),
                "Sponsorship Category":  _safe(row.get("sponsorship_category")),
                "Suggested Ask":         _safe(row.get("suggested_ask")),
                "Sponsorship Fit Score": _safe(row.get("sponsorship_fit_score")),
                "Response Likelihood":   _safe(row.get("response_likelihood")),
                "Confidence":            _safe(row.get("confidence")),
                "Notes":                 _safe(row.get("notes")),
            })
            written += 1
    logger.info(f"Research CSV written: {path} ({written} rows)")


def write_outreach_csv(rows: List[Dict], path: Path):
    """rows is a list of merged (company + research + email) dicts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTREACH_COLS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            r = row.get("research", {})
            e = row.get("emails", {})
            c = row.get("company", {})
            
            poc_email = r.get("poc_email")
            if not poc_email or poc_email.lower().strip() in ("unknown", "none"):
                poc_email = c.get("E-Mail")
                
            email_val = _safe(poc_email).strip().lower()
            if not email_val or email_val in ("unknown", "none", "missing", ""):
                continue
                
            poc_name = r.get("poc_name")
            if not poc_name or poc_name.lower().strip() in ("unknown", "none"):
                poc_name = c.get("POC")
                
            poc_phone = r.get("poc_phone")
            if not poc_phone or poc_phone.lower().strip() in ("unknown", "none"):
                poc_phone = c.get("Phone No.")

            writer.writerow({
                "Company Name":       _safe(c.get("Company Name")),
                "POC":                _safe(poc_name),
                "Email":              _safe(poc_email),
                "Phone":              _safe(poc_phone),
                "Email Subject":      _safe(e.get("email_subject")),
                "Personalized Email": _safe(e.get("personalized_email")),
                "Follow Up Email":    _safe(e.get("follow_up_email")),
                "Sponsorship Fit Score": _safe(r.get("sponsorship_fit_score")),
                "Priority Category":  _safe(r.get("priority_category")),
            })
            written += 1
    logger.info(f"Outreach CSV written: {path} ({written} rows)")


def update_master_csv(research_rows: List[Dict], path: Path):
    """
    Enriches/updates the master input CSV file with found/inferred details,
    preserving all existing columns and other user fields intact.
    """
    if not path.exists():
        logger.warning(f"Master CSV file not found at: {path}")
        return

    # Load all rows from the master CSV to preserve structure
    try:
        with open(path, "r", newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            rows = list(reader)
    except Exception as e:
        logger.error(f"Failed to read master CSV for enrichment: {e}")
        return

    if not rows:
        return

    header = rows[0]
    col_map = {}
    for idx, col in enumerate(header):
        cleaned_col = col.strip().lower()
        if "company name" in cleaned_col:
            col_map["company_name"] = idx
        elif "poc" == cleaned_col:
            col_map["poc"] = idx
        elif "e-mail" == cleaned_col or "email" == cleaned_col:
            col_map["email"] = idx
        elif "phone" in cleaned_col:
            col_map["phone"] = idx
        elif "linkdlin" in cleaned_col or "linkedin" in cleaned_col:
            col_map["linkedin"] = idx
        elif "website" in cleaned_col:
            col_map["website"] = idx

    # Map company names to their research results
    research_by_company = {}
    for r in research_rows:
        name = r.get("_company_name") or r.get("company_name") or ""
        if name:
            research_by_company[name.lower().strip()] = r

    updated_count = 0
    for idx in range(1, len(rows)):
        row = rows[idx]
        if not row:
            continue

        comp_name_idx = col_map.get("company_name")
        if comp_name_idx is None or comp_name_idx >= len(row):
            continue

        cname = row[comp_name_idx].strip()
        cname_key = cname.lower().strip()

        if cname_key in research_by_company:
            res = research_by_company[cname_key]

            # 1. Update POC name + title: format 'Name (Title)'
            poc_idx = col_map.get("poc")
            if poc_idx is not None and poc_idx < len(row):
                new_poc_name = res.get("poc_name", "").strip()
                new_poc_title = res.get("poc_title", "").strip()
                if new_poc_name and new_poc_name.lower() not in ("unknown", "none", "missing"):
                    if new_poc_title and new_poc_title.lower() not in ("unknown", "none", "missing"):
                        new_poc_val = f"{new_poc_name} ({new_poc_title})"
                    else:
                        new_poc_val = new_poc_name
                    row[poc_idx] = new_poc_val

            # 2. Update E-Mail
            email_idx = col_map.get("email")
            if email_idx is not None and email_idx < len(row):
                new_email = res.get("poc_email", "").strip()
                if new_email and new_email.lower() not in ("unknown", "none", "missing"):
                    row[email_idx] = new_email

            # 3. Update Phone No.
            phone_idx = col_map.get("phone")
            if phone_idx is not None and phone_idx < len(row):
                new_phone = res.get("poc_phone", "").strip()
                if new_phone and new_phone.lower() not in ("unknown", "none", "missing"):
                    row[phone_idx] = new_phone

            # 4. Update Linkdlin (matching spelling in input CSV)
            linkedin_idx = col_map.get("linkedin")
            if linkedin_idx is not None and linkedin_idx < len(row):
                new_linkedin = res.get("poc_linkedin", "").strip()
                if new_linkedin and new_linkedin.lower() not in ("unknown", "none", "missing"):
                    row[linkedin_idx] = new_linkedin

            # 5. Update Website
            website_idx = col_map.get("website")
            if website_idx is not None and website_idx < len(row):
                new_website = res.get("website", "").strip()
                if new_website and new_website.lower() not in ("unknown", "none", "missing"):
                    row[website_idx] = new_website

            updated_count += 1

    try:
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerows(rows)
        logger.info(f"Updated {updated_count} rows in master CSV: {path}")
    except Exception as e:
        logger.error(f"Failed to write updated master CSV back: {e}")

