from __future__ import annotations
from pathlib import Path
import json, pandas as pd

def list_group_reports(root: Path) -> list[str]:
    return sorted([p.name for p in root.glob("group_*.html")])

def t1w_metrics(root: Path) -> pd.DataFrame:
    rows = []
    for j in root.glob("sub-*_T1w.json"):
        try:
            d = json.loads(j.read_text())
            subj = d.get("bids_name", j.stem.split("_")[0])
            rows.append({"subject": subj, "cjv": d.get("cjv")})
        except Exception:
            pass
    return pd.DataFrame(rows).sort_values("subject")
