import json
from pathlib import Path
from flux_notebooks.config import Settings

S = Settings.from_env()
DATA_ROOT = Path(S.dataset_root) / "qc" / "mriqc"

def get_qc_summary(sub_id):
    """Aggregate basic MRIQC metrics by modality for a subject."""
    sub_dir = DATA_ROOT / sub_id
    if not sub_dir.exists():
        return {}

    metrics = {"T1w": {}, "BOLD": {}, "DWI": {}}

    for json_file in sub_dir.rglob("*.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)
            name = json_file.name.lower()
            if "t1w" in name:
                metrics["T1w"]["cnr"] = data.get("cnr")
                metrics["T1w"]["snr_total"] = data.get("snr_total")
            elif "bold" in name:
                metrics["BOLD"]["fd_mean"] = data.get("fd_mean")
                metrics["BOLD"]["tsnr"] = data.get("tsnr")
            elif "dwi" in name:
                metrics["DWI"]["snr_total"] = data.get("snr_total")
        except Exception:
            continue
    return metrics
