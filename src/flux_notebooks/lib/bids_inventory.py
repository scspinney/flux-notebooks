from pathlib import Path
from flux_notebooks.config import Settings

S = Settings.from_env()
DATA_ROOT = Path(S.dataset_root) / "bids"
DERIV_ROOT = Path(S.dataset_root) / "derivatives"

def summarize_subject_inventory(sub_id: str):
    """Return high-level info about what data exists for this subject."""
    sub_path = DATA_ROOT / sub_id
    if not sub_path.exists():
        return {"Sessions": "—", "Acquisitions": "—", "Tasks": "—", "Echoes": "—"}

    sessions = sorted([p.name for p in sub_path.glob("ses-*") if p.is_dir()])
    n_sessions = len(sessions)

    acquisitions = set()
    tasks = set()
    echo_counts = {}

    for ses in sessions:
        ses_dir = sub_path / ses
        for mod in ["anat", "func", "dwi"]:
            mod_dir = ses_dir / mod
            if not mod_dir.exists():
                continue
            for f in mod_dir.glob("*.json"):
                fname = f.name
                if "_T1w" in fname:
                    acquisitions.add("T1w")
                elif "_bold" in fname:
                    acquisitions.add("BOLD")
                    if "_task-" in fname:
                        task = fname.split("_task-")[1].split("_")[0]
                        tasks.add(task)
                    if "_echo-" in fname:
                        task = fname.split("_task-")[1].split("_")[0] if "_task-" in fname else "unknown"
                        echo_counts[task] = echo_counts.get(task, 0) + 1
                elif "_dwi" in fname:
                    acquisitions.add("DWI")

    fmriprep_path = DERIV_ROOT / "fmriprep" / sub_id
    fmriprep_exists = fmriprep_path.exists()

    return {
        "Sessions": n_sessions,
        "Session IDs": ", ".join(sessions) if sessions else "—",
        "Acquisitions": ", ".join(sorted(acquisitions)) if acquisitions else "—",
        "Tasks": ", ".join(sorted(tasks)) if tasks else "—",
       # "Echoes per Task": ", ".join([f"{t}:{n}" for t, n in echo_counts.items()]) if echo_counts else "—",
        "Has fMRIPrep": "✅" if fmriprep_exists else "❌",
    }
