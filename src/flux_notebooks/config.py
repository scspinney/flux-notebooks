from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import BaseModel


class Settings(BaseModel):
    dataset_root: Path
    outdir: Path
    validate_bids: bool = False
    enable_plugins: List[str] = []  # e.g., ["bids_validator"]
