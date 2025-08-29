from __future__ import annotations

from pathlib import Path
from typing import Optional

import datalad.api as dl


def clone_or_open(source: str | Path, path: Path, rev: Optional[str] = None) -> dl.Dataset:
    """
    Clone a DataLad dataset from URL or open a local path. Optional checkout of a revision.
    """
    if Path(source).exists():
        ds = dl.Dataset(str(Path(source).resolve()))
        if not ds.is_installed():
            raise RuntimeError(f"Path exists but not a DataLad dataset: {source}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        ds = dl.clone(source=str(source), path=str(path))
    if rev:
        ds.repo.call_git(["checkout", rev])
    return ds
