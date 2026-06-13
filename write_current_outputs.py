#!/usr/bin/env python3
import sys
from pathlib import Path

# Ensure project root is in the path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from src.checkpoint_manager import CheckpointManager
from src.output_writer import write_research_csv, write_outreach_csv

def main():
    print("Loading checkpoint...")
    checkpoint = CheckpointManager(
        Path(settings.BASE_DIR) / "cache",
        settings.CHECKPOINT_EVERY,
    )
    
    if checkpoint.processed_count == 0:
        print("No companies processed in the checkpoint yet.")
        return

    research_preview = Path(settings.BASE_DIR) / "output" / "companies_research_preview.csv"
    outreach_preview = Path(settings.BASE_DIR) / "output" / "companies_outreach_preview.csv"

    print(f"Writing {checkpoint.processed_count} processed records to preview files...")
    write_research_csv(checkpoint.research_rows, research_preview)
    write_outreach_csv(checkpoint.outreach_rows, outreach_preview)
    
    print("\n" + "=" * 50)
    print("Success! Preview files generated:")
    print(f"  Research Preview : {research_preview}")
    print(f"  Outreach Preview : {outreach_preview}")
    print("=" * 50)

if __name__ == "__main__":
    main()
