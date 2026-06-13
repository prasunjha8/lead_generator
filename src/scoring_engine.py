"""
Sponsorship fit scoring and priority classification.
"""

from typing import Dict


def classify_priority(score: int) -> str:
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    else:
        return "D"


def classify_priority_label(score: int) -> str:
    if score >= 90:
        return "A+ — Highest Priority"
    elif score >= 80:
        return "A — Strong Prospect"
    elif score >= 70:
        return "B — Good Prospect"
    elif score >= 60:
        return "C — Moderate Prospect"
    else:
        return "D — Low Priority"


def safe_int(val, default=0) -> int:
    try:
        if val is None:
            return default
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return default


def enrich_research(research: Dict) -> Dict:
    """Ensure all expected fields exist and add derived fields."""
    score = safe_int(research.get("sponsorship_fit_score", 0))
    research["sponsorship_fit_score"]  = max(0, min(100, score))
    research["priority_category"]      = classify_priority(score)
    research["priority_label"]         = classify_priority_label(score)
    research["robotics_relevance_score"]    = max(0, min(10, safe_int(research.get("robotics_relevance_score", 0))))
    research["engineering_relevance_score"] = max(0, min(10, safe_int(research.get("engineering_relevance_score", 0))))
    research["confidence_score"]            = max(0, min(100, safe_int(research.get("confidence_score", 0))))
    return research
