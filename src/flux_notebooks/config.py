# src/flux_notebooks/config.py
from __future__ import annotations
from pathlib import Path
import os
from pydantic import BaseModel, Field, ValidationError


class Settings(BaseModel):
    dataset_root: Path = Field(..., description="Path to the BIDS dataset root")
    outdir: Path = Field(..., description="Where to write notebook artifacts (CSVs, etc.)")

    @classmethod
    def from_env(cls) -> "Settings":
        """
        Construct Settings from environment variables:
          - FLUX_DATASET_ROOT (required)
          - FLUX_OUTDIR (optional; defaults to 'book/notebooks')
        """
        root_env = os.environ.get("FLUX_DATASET_ROOT", "").strip()
        if not root_env:
            raise RuntimeError(
                "FLUX_DATASET_ROOT is not set. Export it, e.g.\n"
                "  export FLUX_DATASET_ROOT=\"$PWD/superdemo\""
            )
        dataset_root = Path(root_env).expanduser().resolve()

        outdir_env = os.environ.get("FLUX_OUTDIR", "book/notebooks").strip()
        outdir = Path(outdir_env).expanduser().resolve()
        outdir.mkdir(parents=True, exist_ok=True)

        try:
            return cls(dataset_root=dataset_root, outdir=outdir)
        except ValidationError as e:
            raise RuntimeError(f"Invalid Settings: {e}") from e

    def as_env(self) -> dict[str, str]:
        """Handy for subprocesses."""
        return {
            "FLUX_DATASET_ROOT": str(self.dataset_root),
            "FLUX_OUTDIR": str(self.outdir),
        }
