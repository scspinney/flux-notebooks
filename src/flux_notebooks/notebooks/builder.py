from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
import pandas as pd
import nbformat as nbf
from jinja2 import Environment, FileSystemLoader


def render_notebook(template_dir: Path, template_name: str, context: Dict[str, Any]) -> nbf.NotebookNode:
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    tpl = env.get_template(template_name)
    ipynb_json = tpl.render(**context)
    return nbf.reads(ipynb_json, as_version=4)


def write_notebook(nb: nbf.NotebookNode, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        nbf.write(nb, f)


def save_tables(summary: Dict[str, Any], outdir: Path) -> None:
    def _save_df(name: str):
        df = summary.get(name)
        if df is not None and hasattr(df, "empty") and not df.empty:
            df.reset_index().to_csv(outdir / f"{name}.csv", index=False)

    # Existing tables
    _save_df("avail")
    _save_df("func_counts")

    # New: richer tables
    _save_df("size_by_datatype")
    _save_df("counts_by_suffix")
    _save_df("tr_by_task")

    # Participants if present
    df = summary.get("participants")
    if isinstance(df, pd.DataFrame) and not df.empty:
        df.to_csv(outdir / "participants.tsv", sep="\t", index=False)

    # Dataset description for completeness
    dd = summary.get("dataset_description")
    if isinstance(dd, dict) and dd:
        (outdir / "dataset_description.json").write_text(json.dumps(dd, indent=2))

