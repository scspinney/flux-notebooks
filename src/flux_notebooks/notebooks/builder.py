# src/flux_notebooks/notebooks/builder.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Callable
import nbformat as nbf
import pandas as pd


Section = Callable[[Dict[str, Any]], Iterable[nbf.NotebookNode]]

def new_notebook(cells: List[nbf.NotebookNode]) -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb["cells"] = cells
    nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    return nb

def build_from_sections(context: Dict[str, Any], sections: List[Section]) -> nbf.NotebookNode:
    cells: List[nbf.NotebookNode] = []
    for sec in sections:
        cells.extend(list(sec(context)))
    return new_notebook(cells)

def write_notebook(nb: nbf.NotebookNode, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        nbf.write(nb, f)


def save_tables(summary: Dict[str, Any], outdir: Path) -> None:
    """
    Shared CSV dumping helper. Templates may call this if they compute these tables.
    Safe to call even if tables are missing/empty.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    if isinstance(summary.get("avail"), pd.DataFrame) and not summary["avail"].empty:
        summary["avail"].to_csv(outdir / "avail.csv", index=False)
    if isinstance(summary.get("func_counts"), pd.DataFrame) and not summary["func_counts"].empty:
        summary["func_counts"].to_csv(outdir / "func_counts.csv", index=True)
    if isinstance(summary.get("tr_by_task"), pd.DataFrame) and not summary["tr_by_task"].empty:
        summary["tr_by_task"].to_csv(outdir / "tr_by_task.csv", index=False)
