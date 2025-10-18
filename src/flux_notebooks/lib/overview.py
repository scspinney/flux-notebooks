from pathlib import Path
import json

def summarize_dataset(dataset_root: Path):
    """Summarize subjects, sessions, tasks, and modalities from a BIDS dataset."""
    bids_root = (
        dataset_root
        if (dataset_root / "dataset_description.json").exists()
        else (dataset_root / "bids")
    )
    subjects = sorted([p.name for p in bids_root.glob("sub-*") if p.is_dir()])
    n_subjects = len(subjects)

    sessions = set()
    tasks = set()
    modalities = set()

    for sub in subjects:
        sub_path = bids_root / sub
        for ses in sub_path.glob("ses-*"):
            sessions.add(ses.name)
            for mod_dir in ses.glob("*"):
                if not mod_dir.is_dir():
                    continue
                for f in mod_dir.glob("*"):
                    fname = f.name.lower()
                    if "_task-" in fname:
                        tasks.add(fname.split("_task-")[1].split("_")[0])
                    if "_t1w" in fname:
                        modalities.add("T1w")
                    elif "_bold" in fname:
                        modalities.add("BOLD")
                    elif "_dwi" in fname:
                        modalities.add("DWI")
                    elif "_flair" in fname:
                        modalities.add("FLAIR")

    # Count FreeSurfer subjects if available
    fs_dir = dataset_root / "derivatives" / "freesurfer"
    n_fs_subjects = len(list(fs_dir.glob("sub-*"))) if fs_dir.exists() else 0

    # Derive a naive “completion” metric
    completion = 0
    if n_subjects:
        completion = round(min(100 * n_fs_subjects / n_subjects, 100))

    return {
        "subjects": n_subjects,
        "sessions": len(sessions),
        "tasks": sorted(tasks),
        "modalities": sorted(modalities),
        "freesurfer_subjects": n_fs_subjects,
        "completion_percent": completion,
    }
