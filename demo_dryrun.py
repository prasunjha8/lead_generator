"""
Demo dry-run: verifies the full pipeline works without any API calls.
Injects mock research + email data for one company and writes output CSVs.
Run: python demo_dryrun.py
"""
import sys
sys.path.insert(0, ".")

from src.csv_loader import load_companies
from src.cache_manager import CacheManager
from src.checkpoint_manager import CheckpointManager
from src.scoring_engine import enrich_research
from src.output_writer import write_research_csv, write_outreach_csv
from pathlib import Path

MOCK_RESEARCH = {
    "company_summary": "Robu.in is a leading Indian online retailer for robotics components, microcontrollers, sensors, and electronics targeting students and engineers.",
    "industry": "Electronics & Robotics Components Retail",
    "products_services": "Arduino, Raspberry Pi, servo motors, BLDC motors, ESCs, LiPo batteries, sensors, robot chassis kits",
    "company_size": "SME",
    "target_market": "Students, robotics enthusiasts, engineering colleges, makers",
    "technologies_used": "E-commerce, embedded systems hardware, IoT components",
    "robotics_relevance_score": 10,
    "engineering_relevance_score": 9,
    "sponsorship_fit_score": 92,
    "potential_sponsorship_types": ["Electronics Components", "Motors", "Motor Controllers", "Batteries", "Sensors"],
    "potential_sponsorship_value": "Medium (50k-2L INR)",
    "why_company_should_sponsor": "Robu.in serves exactly the audience Robolution represents — engineering students passionate about robotics. Sponsoring gives direct brand exposure to their core customer base.",
    "why_robolution_is_relevant": "BIT Mesra students are the demographic that purchases Robu products. A winning Robowars team is a real-world advertisement for the components it uses.",
    "how_company_can_help": "Component sponsorship (motors, ESCs, sensors, LiPo batteries) and co-marketing through social channels.",
    "what_value_robolution_provides": "Brand visibility at BIT Mesra, social media content, logo on team jersey, RoboSaga festival presence, competition testimonials.",
    "suggested_sponsorship_strategy": "Lead with component sponsorship — easier yes than cash. Offer Instagram reels and RoboSaga exhibition visibility.",
    "suggested_talking_points": ["Components power competitive robotics", "BIT Mesra has 3000+ students", "RoboSaga reaches 5000+ attendees", "ABU ROBOCON national exposure"],
    "csr_alignment": "STEM education and student skill development.",
    "recruitment_angle": "Access to BIT Mesra students for internships.",
    "research_notes": "Highest-fit sponsor. Product-audience alignment is perfect.",
    "confidence_score": 95,
    "research_source": "ddg_search",
    "_company_name": "Robu.in",
    "poc_name": "Nilesh Chauhan",
    "poc_title": "Founder & Director",
    "poc_email": "nilesh@robu.in",
    "poc_phone": "90498 14349",
    "poc_linkedin": "https://www.linkedin.com/in/nilesh-chauhan-robu/",
    "student_program": "Yes: sponsors college student teams",
    "sponsorship_program": "Yes: active student sponsorship program",
    "sponsorship_category": "Components",
    "suggested_ask": "Free motors and ESCs",
    "response_likelihood": "High",
    "confidence": "High",
    "notes": "Excellent product-audience alignment",
}

MOCK_EMAIL = {
    "email_subject": "Robolution x Robu.in — Powering India's Next Competitive Robotics Team",
    "personalized_email": (
        "Dear Nilesh,\n\n"
        "I hope this message finds you well.\n\n"
        "I am Prasun Jha, writing on behalf of Robolution — the official robotics and innovation club of BIT Mesra, and our institute's representative team for ABU ROBOCON.\n\n"
        "I am reaching out because Robu.in is not just a supplier to teams like ours — it is a platform built for exactly the kind of engineers our club trains. Your inventory of BLDC motors, ESCs, LiPo packs, and sensor modules is what competitive robotics teams depend on. That alignment is why I believe a partnership makes genuine sense for both of us.\n\n"
        "Our Robowars journey has been rapid: first-time participation in 2024, national Quarter Finals in 2025, and a podium target for 2026 with expanded multi-institution presence. Behind every milestone is hardware — the kind you stock.\n\n"
        "We are seeking component sponsorship (motors, ESCs, batteries, sensors) and / or a monetary partnership to build a stronger machine for 2026. In exchange: logo placement on the robot and team jersey, dedicated social media features, live coverage at RoboSaga festival, and genuine testimonial content showing Robu components under competition conditions.\n\n"
        "To provide a detailed overview of our team, achievements, sponsorship opportunities, and visibility offerings, we have attached our sponsorship brochure for your reference.\n\n"
        "Would you be open to a 15-minute call this week?\n\n"
        "Warm regards,\n"
        "Prasun Jha\n"
        "Robolution | BIT Mesra | Team Pratyunmis"
    ),
    "follow_up_subject": "Following Up — Robolution Sponsorship | Robu.in",
    "follow_up_email": (
        "Dear Nilesh,\n\n"
        "I wanted to follow up on my earlier email about a partnership between Robu.in and Robolution, BIT Mesra.\n\n"
        "One addition: our 2026 campaign spans multiple competitions — each event an opportunity to showcase components in action, with footage we are happy to share on your channels.\n\n"
        "Would you be available for a brief 10-minute call this week?\n\n"
        "Thank you for your time.\n\n"
        "Warm regards,\n"
        "Prasun Jha\n"
        "Robolution | BIT Mesra"
    ),
}

if __name__ == "__main__":
    companies = load_companies(Path("data/input.csv"))
    company = companies[0]  # Robu.in

    cache = CacheManager(Path("cache/research_cache.db"), 720)
    checkpoint = CheckpointManager(Path("cache"), 5)

    research = enrich_research(MOCK_RESEARCH)
    checkpoint.mark_processed(company["Company Name"], research, company, MOCK_EMAIL)

    write_research_csv(checkpoint.research_rows, Path("output/companies_research.csv"))
    write_outreach_csv(checkpoint.outreach_rows, Path("output/companies_outreach.csv"))

    print("Demo dry-run complete.")
    print(f"  Research rows : {len(checkpoint.research_rows)}")
    print(f"  Outreach rows : {len(checkpoint.outreach_rows)}")
    print(f"  Fit score     : {research['sponsorship_fit_score']} | Priority: {research['priority_category']}")
    print(f"  Output files  : output/companies_research.csv, output/companies_outreach.csv")
