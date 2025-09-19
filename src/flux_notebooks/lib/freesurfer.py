from __future__ import annotations
from pathlib import Path
import pandas as pd

def subjects_table(root: Path) -> pd.DataFrame:
    rows = []
    for subj in sorted([p for p in root.glob("sub-*") if p.is_dir()]):
        aseg = subj / "stats" / "aseg.stats"
        rows.append({"subject": subj.name, "has_aseg_stats": aseg.exists()})
    return pd.DataFrame(rows)

def aseg_summary(root: Path) -> pd.DataFrame:
    rows = []
    for subj in sorted([p for p in root.glob("sub-*") if p.is_dir()]):
        stats = subj/"stats"/"aseg.stats"
        if not stats.exists(): 
            continue
        d = {"subject": subj.name}
        for line in stats.read_text().splitlines():
            if "BrainSegVol" in line and "mm^3" in line:
                try: d["BrainSegVol"] = float(line.split(",")[2])
                except: pass
            if "eTIV" in line and "mm^3" in line:
                try: d["eTIV"] = float(line.split(",")[2])
                except: pass
        rows.append(d)
    return pd.DataFrame(rows).sort_values("subject") if rows else pd.DataFrame()
