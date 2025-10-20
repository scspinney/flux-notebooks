#!/usr/bin/env python3
"""
Subject demographic loader for Flux Dashboards.

Priority of data sources:
1. Youth behavioural TSV (self-report)
2. Caregiver-reported child fields (demo_ethnicity, demo_sex, demo_home_lang)
3. REDCap CSV fallback
4. Missing → "—"

Caregiver self fields (demo_cg_*) are ignored.
"""

from pathlib import Path
import pandas as pd
from flux_notebooks.config import Settings

# ─────────────────────────────────────────────────────────────────────────────
# Global configuration
# ─────────────────────────────────────────────────────────────────────────────
S = Settings.from_env()
DATA_ROOT = Path(S.dataset_root)
BIDS_ROOT = DATA_ROOT / "bids"

# ─────────────────────────────────────────────────────────────────────────────
# Lookup tables
# ─────────────────────────────────────────────────────────────────────────────
SEX_MAP = {
    "1": "Male",
    "2": "Female",
    "3": "Intersex / Non-binary",
    "777": "Don't know",
    "888": "Prefer not to say",
}

ETHNICITY_MAP = {
    "1": "Black",
    "2": "East Asian",
    "3": "First Nations",
    "4": "Inuk/Inuit",
    "5": "Métis",
    "6": "Latin American",
    "7": "Middle Eastern",
    "8": "South Asian",
    "9": "Southeast Asian",
    "10": "White",
    "11": "Other",
    "888": "Prefer not to say",
    "white": "White",
    "black": "Black",
    "asian": "Asian",
}

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read_tsv(path: Path) -> pd.DataFrame:
    """Read TSV file safely, normalizing all values to clean strings."""
    try:
        df = pd.read_csv(path, sep="\t", dtype=str).fillna("")

        def _norm(v):
            s = str(v).strip()
            if s in ("", "nan", "NaN"):
                return ""
            try:
                f = float(s)
                return str(int(f)) if f.is_integer() else str(f)
            except Exception:
                return s

        return df.map(_norm)
    except Exception as e:
        print(f"[ERROR] Failed to read {path}: {e}")
        return pd.DataFrame()


def _load_demo_tsv(sub_id: str) -> dict:
    """
    Load subject demographics from BIDS behavioural TSVs.

    Priority:
      1. Youth self-report (_task-youth_beh.tsv)
      2. Caregiver-reported child fields (_task-demo_beh.tsv)
    """
    subj_dir = BIDS_ROOT / sub_id
    if not subj_dir.exists():
        print(f"[BEH] Subject folder not found: {sub_id}")
        return {}

    youth_file = next(subj_dir.glob("ses-*/beh/*_task-youth_beh.tsv"), None)
    demo_file = next(subj_dir.glob("ses-*/beh/*_task-demo_beh.tsv"), None)

    youth_df = _read_tsv(youth_file) if youth_file else pd.DataFrame()
    demo_df = _read_tsv(demo_file) if demo_file else pd.DataFrame()

    youth = youth_df.iloc[0] if not youth_df.empty else pd.Series()
    demo = demo_df.iloc[0] if not demo_df.empty else pd.Series()

    # ─── Age ────────────────────────────────────────────────────────────────
    age_str = "—"
    if not youth.empty:
        try:
            y = float(youth.get("youth_age_y", "") or 0)
            m = float(youth.get("youth_age_m", "") or 0)
            if y or m:
                age_str = f"{y + m / 12:.1f}"
        except Exception:
            pass

    # ─── Home Language ─────────────────────────────────────────────────────
    lang = "—"
    if not youth.empty and youth.get("youth_prefer_lang", ""):
        lang = youth["youth_prefer_lang"].capitalize()
    elif not demo.empty:
        for k in demo.keys():
            if k.startswith("demo_home_lang___") and demo[k] == "1":
                lang = "Fr" if "2" in k else "En"
                break
        if lang == "—" and demo.get("demo_home_lang_oth", ""):
            lang = demo["demo_home_lang_oth"].capitalize()

    # ─── Ethnicity ─────────────────────────────────────────────────────────
    ethnicity = "—"
    if not demo.empty:
        for k in demo.keys():
            if k.startswith("demo_ethnicity___") and demo[k] == "1":
                code = k.split("___")[-1]
                ethnicity = ETHNICITY_MAP.get(code, "Other")
                break

    # ─── Sex ───────────────────────────────────────────────────────────────
    sex = "—"
    if not demo.empty and demo.get("demo_sex", ""):
        code = demo["demo_sex"].strip()
        sex = SEX_MAP.get(code, code)

    # ─── Other demographic fields ──────────────────────────────────────────
    origin = demo.get("demo_origin", "—") if not demo.empty else "—"
    yrs_can = demo.get("demo_yrs_can", "—") if not demo.empty else "—"

    return {
        "Sex": sex,
        "Age (yrs)": age_str,
        "Ethnicity": ethnicity,
        "Home Language": lang,
        # "Country of Origin": origin,
        # "Years in Canada": yrs_can,
    }


# ─────────────────────────────────────────────────────────────────────────────
# REDCap fallback loader
# ─────────────────────────────────────────────────────────────────────────────
def _load_redcap_df() -> pd.DataFrame:
    """Load all REDCap CSVs from the data/redcap folder."""
    redcap_dir = DATA_ROOT / "data" / "redcap"
    if not redcap_dir.exists():
        return pd.DataFrame()

    files = list(redcap_dir.glob("*.csv"))
    if not files:
        return pd.DataFrame()

    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, dtype=str).fillna("")
            df.columns = [c.lower().strip() for c in df.columns]
            dfs.append(df)
        except Exception as e:
            print(f"[REDCAP] Failed to read {f}: {e}")

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def _load_redcap_info(sub_id: str) -> dict:
    """Lookup participant info in REDCap CSV exports."""
    df = _load_redcap_df()
    if df.empty:
        return {}

    pid_col = next(
        (c for c in df.columns if c in ["record_id", "participant_id", "cpip_id", "subid", "sub_id"]),
        None,
    )
    if pid_col is None:
        return {}

    variants = {sub_id, sub_id.replace("sub-", ""), f"sub-{sub_id}"}
    sub = df[df[pid_col].astype(str).isin(variants)]
    if sub.empty:
        return {}

    row = sub.iloc[0]
    fields = ["age", "sex", "ethnicity", "language", "origin", "years_in_canada"]
    return {f.capitalize(): row.get(f, "—") for f in fields if f in df.columns}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────
def get_subject_info(sub_id: str) -> dict:
    """
    Return demographic info for a subject, preferring BIDS behavioural data,
    then falling back to REDCap exports.
    """
    info = _load_demo_tsv(sub_id)
    if info:
        print(f"[INFO] Loaded demographics from BIDS for {sub_id}")
        return info

    info = _load_redcap_info(sub_id)
    if info:
        print(f"[INFO] Loaded demographics from REDCap for {sub_id}")
        return info

    print(f"[INFO] No demographic info found for {sub_id}")
    return {}


def get_subject_list(site: str = None) -> list[str]:
    """
    Return all subjects from the BIDS dataset.
    If `site` is provided, filter using participants.tsv.
    """
    if not BIDS_ROOT.exists():
        print(f"[BIDS] Dataset root not found: {BIDS_ROOT}")
        return []

    subs = sorted([p.name for p in BIDS_ROOT.glob("sub-*") if p.is_dir()])

    if site:
        participants_file = BIDS_ROOT / "participants.tsv"
        if participants_file.exists():
            df = pd.read_csv(participants_file, sep="\t", dtype=str).fillna("")
            if "site_name" in df.columns and "participant_id" in df.columns:
                df_site = df[df["site_name"].str.lower() == site.lower()]
                subs = sorted(df_site["participant_id"].tolist())

    print(f"[BIDS] Found {len(subs)} subjects (site={site or 'all'})")
    return subs
