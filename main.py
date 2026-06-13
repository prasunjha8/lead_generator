#!/usr/bin/env python3
"""
Robolution Sponsorship Intelligence System
==========================================
Production-grade pipeline for automated sponsorship research and outreach.

Usage:
    python main.py                        # Run full pipeline (research + emails)
    python main.py --phase research       # Research only
    python main.py --phase email          # Email generation only (needs research done)
    python main.py --force-refresh        # Reprocess all companies ignoring cache
    python main.py --batch-size 3         # Override concurrency setting
    python main.py --limit 20            # Process only first N companies (useful for testing)
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict

from tqdm.asyncio import tqdm as atqdm
from tqdm import tqdm

# ── ensure project root is on the path ────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from src.log_setup import setup_logging
from src.csv_loader import load_companies
from src.cache_manager import CacheManager
from src.checkpoint_manager import CheckpointManager
from src.llm_router import LLMRouter
from src.research_engine import research_company
from src.email_generator import generate_emails
from src.scoring_engine import enrich_research
from src.output_writer import write_research_csv, write_outreach_csv, update_master_csv

logger = logging.getLogger(__name__)


# ── Pipeline workers ───────────────────────────────────────────────────────────

async def process_one_company(
    company: Dict,
    llm: LLMRouter,
    cache: CacheManager,
    force_refresh: bool = False,
) -> tuple[Dict, Dict]:
    """
    Research + email generation for a single company.
    Returns (research_result, email_result).
    """
    name     = company["Company Name"]
    website  = company.get("Website", "")
    linkedin = company.get("LinkedIn", "")

    # ── Research phase ──────────────────────────────────────────────────────
    research = None if force_refresh else cache.get_research(name, website, linkedin)

    if research:
        logger.info(f"[CACHE HIT] Research: {name}")
    else:
        logger.info(f"[RESEARCH ] Processing: {name}")
        t0 = time.time()
        research = await research_company(company, llm)
        elapsed  = time.time() - t0
        logger.info(f"[RESEARCH ] Done: {name} ({elapsed:.1f}s) "
                    f"score={research.get('sponsorship_fit_score', 0)}")
        if research:
            cache.set_research(name, research, website, linkedin)

    if not research:
        research = {}

    research = enrich_research(research)

    # ── Email phase ─────────────────────────────────────────────────────────
    emails = None if force_refresh else cache.get_emails(name, website, linkedin)

    if emails:
        logger.info(f"[CACHE HIT] Emails: {name}")
    else:
        logger.info(f"[EMAIL GEN] Generating: {name}")
        emails = await generate_emails(company, research, llm)
        if emails:
            cache.set_emails(name, emails, website, linkedin)

    if not emails:
        emails = {}

    return research, emails


async def run_research_phase(
    companies: List[Dict],
    llm: LLMRouter,
    cache: CacheManager,
    checkpoint: CheckpointManager,
    batch_size: int,
    force_refresh: bool,
):
    """Process companies in concurrent batches with progress bar."""
    pending = [c for c in companies if not checkpoint.is_processed(c["Company Name"])]

    logger.info(f"Total: {len(companies)} | Already done: {checkpoint.processed_count} | "
                f"Remaining: {len(pending)}")

    if not pending:
        logger.info("All companies already processed. Nothing to do.")
        return

    # Process in batches
    with tqdm(total=len(pending), desc="Processing companies", unit="co") as pbar:
        for i in range(0, len(pending), batch_size):
            batch = pending[i: i + batch_size]

            tasks = [
                process_one_company(c, llm, cache, force_refresh)
                for c in batch
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for company, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"Failed: {company['Company Name']} — {result}")
                    pbar.update(1)
                    continue

                research, emails = result
                
                # Check email validity
                poc_email = research.get("poc_email", "").strip().lower()
                has_email = poc_email and poc_email not in ("unknown", "missing", "none", "")
                
                # If newly discovered, only add to master input CSV if we have at least an email!
                if company.get("is_discovered"):
                    if not has_email:
                        logger.info(f"Skipping newly discovered company '{company['Company Name']}' - no email found.")
                        pbar.update(1)
                        continue
                    else:
                        try:
                            import csv
                            with open(settings.INPUT_CSV, "a", newline="", encoding="utf-8") as fh:
                                writer = csv.writer(fh)
                                # Append to master input.csv
                                writer.writerow([
                                    company["Company Name"],
                                    research.get("poc_name", "Unknown"),
                                    research.get("poc_email", "Missing"),
                                    research.get("poc_phone", "Missing"),
                                    "",
                                    "",
                                    company["Website"],
                                    "Prasun Jha",
                                    "FALSE",
                                    "",
                                    "FALSE",
                                    "",
                                    "",
                                    ""
                                ])
                            logger.info(f"Appended newly discovered company '{company['Company Name']}' with email '{poc_email}' to master CSV.")
                        except Exception as e:
                            logger.error(f"Failed to append '{company['Company Name']}' to master CSV: {e}")

                checkpoint.mark_processed(
                    company["Company Name"],
                    research,
                    company,
                    emails,
                )
                pbar.update(1)
                pbar.set_postfix({
                    "last": company["Company Name"][:25],
                    "score": research.get("sponsorship_fit_score", "?"),
                })

            # Write incremental outputs after each batch
            try:
                write_research_csv(checkpoint.research_rows, settings.OUTPUT_RESEARCH)
                write_outreach_csv(checkpoint.outreach_rows, settings.OUTPUT_OUTREACH)
                update_master_csv(checkpoint.research_rows, settings.INPUT_CSV)
            except Exception as e:
                logger.warning(f"Failed to write incremental CSV outputs: {e}")

    # Final save
    checkpoint.save(force=True)


# ── Main entry point ───────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Robolution Sponsorship Intelligence System")
    p.add_argument("--phase",         choices=["research", "email", "full"], default="full",
                   help="Which phase to run (default: full)")
    p.add_argument("--force-refresh", action="store_true",
                   help="Ignore cache and reprocess all companies")
    p.add_argument("--batch-size",    type=int, default=None,
                   help="Override BATCH_SIZE from .env")
    p.add_argument("--limit",         type=int, default=None,
                   help="Limit to first N companies (for testing)")
    p.add_argument("--debug",         action="store_true",
                   help="Enable DEBUG log level")
    p.add_argument("--mode",          choices=["enrich", "discover"], default="enrich",
                   help="Workflow mode: 'enrich' (process input CSV) or 'discover' (find new sponsors)")
    p.add_argument("--category",      type=str, default=None,
                   help="Discovery category (e.g. '3D Printing and Rapid Prototyping')")
    p.add_argument("--discover-limit", type=int, default=10,
                   help="Number of new companies to discover")
    return p.parse_args()


async def main():
    args = parse_args()

    # ── Logging ────────────────────────────────────────────────────────────
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(settings.LOG_FILE, log_level)

    logger.info("=" * 60)
    logger.info("  Robolution Sponsorship Intelligence System")
    logger.info("=" * 60)

    # ── Effective settings ─────────────────────────────────────────────────
    batch_size    = args.batch_size or settings.BATCH_SIZE
    force_refresh = args.force_refresh or settings.FORCE_REFRESH

    logger.info(f"Mode         : {args.mode}")
    logger.info(f"Phase        : {args.phase}")
    logger.info(f"Batch size   : {batch_size}")
    logger.info(f"Force refresh: {force_refresh}")

    # ── Load CSV ────────────────────────────────────────────────────────────
    companies = load_companies(settings.INPUT_CSV)
    if args.limit and args.mode != "discover":
        companies = companies[:args.limit]
        logger.info(f"Limited to {args.limit} companies for this run.")

    # ── Initialise components ───────────────────────────────────────────────
    cache = CacheManager(settings.CACHE_DB, settings.CACHE_TTL_HOURS)
    checkpoint = CheckpointManager(
        Path(settings.BASE_DIR) / "cache",
        settings.CHECKPOINT_EVERY,
    )

    if force_refresh:
        logger.info("Force refresh enabled. Clearing checkpoint file.")
        checkpoint.clear()

    llm = LLMRouter(
        gemini_key=settings.GEMINI_API_KEY,
        groq_key=settings.GROQ_API_KEY,
        openrouter_key=settings.OPENROUTER_API_KEY,
        gemini_model=settings.GEMINI_MODEL,
        groq_models=settings.GROQ_MODELS,
        openrouter_models=settings.OPENROUTER_MODELS,
    )

    # ── Run Discovery Mode if selected ──────────────────────────────────────
    if args.mode == "discover":
        logger.info("=" * 60)
        logger.info("  DISCOVERY MODE: Discovering New Sponsors")
        logger.info("=" * 60)

        existing_companies = [c["Company Name"] for c in companies]

        from src.discovery_engine import discover_companies
        discovered = await discover_companies(
            llm=llm,
            limit=args.discover_limit,
            category=args.category,
            existing_companies=existing_companies
        )

        if not discovered:
            logger.error("No companies discovered. Exiting.")
            return

        companies = discovered
        if args.limit:
            companies = companies[:args.limit]
            logger.info(f"Limited discovered list to first {args.limit} companies.")

    # ── Run pipeline ────────────────────────────────────────────────────────
    t_start = time.time()

    await run_research_phase(
        companies, llm, cache, checkpoint,
        batch_size=batch_size,
        force_refresh=force_refresh,
    )

    elapsed = time.time() - t_start

    # ── Write outputs ───────────────────────────────────────────────────────
    write_research_csv(checkpoint.research_rows, settings.OUTPUT_RESEARCH)
    write_outreach_csv(checkpoint.outreach_rows, settings.OUTPUT_OUTREACH)
    update_master_csv(checkpoint.research_rows, settings.INPUT_CSV)

    # ── Summary ─────────────────────────────────────────────────────────────
    cache_stats = cache.stats()
    logger.info("=" * 60)
    logger.info(f"  DONE in {elapsed:.1f}s")
    logger.info(f"  Companies processed : {checkpoint.processed_count}")
    logger.info(f"  Cache DB entries    : {cache_stats['total']}")
    logger.info(f"  Research output     : {settings.OUTPUT_RESEARCH}")
    logger.info(f"  Outreach output     : {settings.OUTPUT_OUTREACH}")
    logger.info("=" * 60)

    # Priority breakdown
    rows = checkpoint.research_rows
    breakdown = {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 0}
    for r in rows:
        p = r.get("priority_category", "D")
        if p in breakdown:
            breakdown[p] += 1

    logger.info("  Priority breakdown:")
    for tier, count in breakdown.items():
        logger.info(f"    {tier}: {count} companies")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
