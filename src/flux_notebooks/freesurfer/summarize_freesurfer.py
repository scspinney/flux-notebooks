from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

def _read_aseg_stats(stats_path: Path) -> Dict[str, float]:
    vals: Dict[str, float] = {}
    if not stats_path.exists():
        return vals
    for line in stats_path.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 4:
            # id, StructName, Volume_mm3, NormMean? (format varies)
            try:
                name = parts[1]
                vol = float(parts[2])
                vals[name] = vol
            except Exception:
                pass
    return vals

def summarize_freesurfer(fs_root: Path) -> Dict[str, Any]:
    fs_root = Path(fs_root)
    subjects: List[str] = sorted([p.name for p in fs_root.glob("sub-*") if p.is_dir()])
    aseg_rows = []
    for sub in subjects:
        stats = fs_root / sub / "stats" / "aseg.stats"
        vals = _read_aseg_stats(stats)
        if vals:
            row = {"subject": sub, **vals}
            aseg_rows.append(row)
    aseg_df = pd.DataFrame(aseg_rows).set_index("subject") if aseg_rows else pd.DataFrame()
    subjects_df = pd.DataFrame({"subject": subjects})
    return {
        "subjects": subjects,
        "subjects_table": subjects_df,
        "aseg_summary": aseg_df,
    }
