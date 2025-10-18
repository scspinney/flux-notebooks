from pathlib import Path
import pandas as pd
from flux_notebooks.config import Settings

S = Settings.from_env()
DATA_ROOT = Path(S.dataset_root)

# Target the canonical BIDS participants.tsv
REDCAP_FILE = DATA_ROOT / "bids" / "participants.tsv"

def load_redcap():
    """Load BIDS participants.tsv or return empty DataFrame."""
    if REDCAP_FILE.exists():
        try:
            df = pd.read_csv(REDCAP_FILE, sep="\t")
            # Normalize columns to lowercase for safety
            df.columns = [c.lower().strip() for c in df.columns]
            if "participant_id" not in df.columns and "participant" in df.columns:
                df = df.rename(columns={"participant": "participant_id"})
            if "participant_id" not in df.columns and "sub_id" in df.columns:
                df = df.rename(columns={"sub_id": "participant_id"})
            df["participant_id"] = df["participant_id"].astype(str)
            return df
        except Exception as e:
            print(f"[REDCAP] Failed to read {REDCAP_FILE}: {e}")
    return pd.DataFrame(columns=["participant_id", "age", "sex", "handedness", "site", "diagnosis"])

def get_subject_info(sub_id: str) -> dict:
    """Get demographic info for subject (expects sub-XXX)."""
    df = load_redcap()
    # BIDS uses "sub-001" format; normalize both ways
    sub_variants = {sub_id, sub_id.replace("sub-", ""), f"sub-{sub_id}"}
    sub = df[df["participant_id"].isin(sub_variants)]
    if sub.empty:
        return {}
    row = sub.iloc[0]
    return {
        "Age": row.get("age", "—"),
        "Sex": row.get("sex", "—"),
        "Handedness": row.get("handedness", "—"),
        "Site": row.get("site", "—"),
        "Diagnosis": row.get("diagnosis", "—"),
    }
