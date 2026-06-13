"""
Checkpoint manager.
Saves progress every N companies to enable safe resumption after interruptions.
"""

import json
import logging
from pathlib import Path
from typing import Set, Dict, List

logger = logging.getLogger(__name__)


class CheckpointManager:
    def __init__(self, checkpoint_dir: Path, checkpoint_every: int = 10):
        self.checkpoint_dir  = checkpoint_dir
        self.checkpoint_every = checkpoint_every
        self._processed: Set[str] = set()
        self._research_rows: List[Dict] = []
        self._outreach_rows: List[Dict] = []
        self._counter = 0

        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def _checkpoint_file(self) -> Path:
        return self.checkpoint_dir / "checkpoint.json"

    def _load(self):
        f = self._checkpoint_file()
        if f.exists():
            try:
                data = json.loads(f.read_text())
                self._processed      = set(data.get("processed", []))
                self._research_rows  = data.get("research_rows", [])
                self._outreach_rows  = data.get("outreach_rows", [])
                logger.info(f"Checkpoint loaded: {len(self._processed)} previously processed companies.")
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}")

    def save(self, force: bool = False):
        if not force and self._counter % self.checkpoint_every != 0:
            return
        data = {
            "processed":     list(self._processed),
            "research_rows": self._research_rows,
            "outreach_rows": self._outreach_rows,
        }
        tmp = self._checkpoint_file().with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        tmp.replace(self._checkpoint_file())
        logger.info(f"Checkpoint saved ({len(self._processed)} companies).")

    def is_processed(self, company_name: str) -> bool:
        return company_name.lower().strip() in self._processed

    def clear(self):
        """Clears the checkpoint memory and deletes the checkpoint file."""
        self._processed = set()
        self._research_rows = []
        self._outreach_rows = []
        self._counter = 0
        f = self._checkpoint_file()
        if f.exists():
            try:
                f.unlink()
                logger.info("Checkpoint file cleared.")
            except Exception as e:
                logger.warning(f"Could not delete checkpoint file: {e}")

    def mark_processed(self, company_name: str,
                        research: Dict, company: Dict, emails: Dict):
        key = company_name.lower().strip()
        self._processed.add(key)
        self._research_rows.append(research)
        self._outreach_rows.append({
            "company":  company,
            "research": research,
            "emails":   emails,
        })
        self._counter += 1
        self.save()

    @property
    def research_rows(self) -> List[Dict]:
        return self._research_rows

    @property
    def outreach_rows(self) -> List[Dict]:
        return self._outreach_rows

    @property
    def processed_count(self) -> int:
        return len(self._processed)
