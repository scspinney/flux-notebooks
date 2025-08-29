from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

import nbformat as nbf
import pandas as pd

from . import sections


def build_summary_notebook(context: Dict[str, Any]) -> nbf.NotebookNode:
    """
    Assemble the BIDS summary notebook from modular sections.
    Expected context keys:
      - dataset_root (Path)
      - outdir (Path)
      - generated (str)
      - n_subjects, n_sessions, n_tasks (ints)
      - datatypes (List[str])
    """
    ds_root: Path = context["dataset_root"]
    outdir: Path = context["outdir"]
    generated: str = context["generated"]
    n_subjects: int = context["n_subjects"]
    n_sessions: int = context["n_sessions"]
    n_tasks: int = context["n_tasks"]
    datatypes: List[str] = context["datatypes"]

    nb = nbf.v4.new_notebook()
    cells: List[nbf.NotebookNode] = []

    cells += list(sections.intro_section(ds_root, generated))
    cells += list(sections.init_section(outdir, n_subjects, n_sessions, n_tasks, datatypes))
    cells += list(sections.metadata_section(ds_root))
    cells += list(sections.kpi_section(ds_root))
    cells += list(sections.availability_section())
    cells += list(sections.func_runs_section())
    cells += list(sections.tr_section())
    cells += list(sections.explorer_section(ds_root))

    nb["cells"] = cells
    nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    return nb


def write_notebook(nb: nbf.NotebookNode, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        nbf.write(nb, f)


def save_tables(summary: Dict[str, Any], outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    if isinstance(summary.get("avail"), pd.DataFrame) and not summary["avail"].empty:
        summary["avail"].to_csv(outdir / "avail.csv", index=False)
    if isinstance(summary.get("func_counts"), pd.DataFrame) and not summary["func_counts"].empty:
        summary["func_counts"].to_csv(outdir / "func_counts.csv", index=True)
