#!/usr/bin/env python3
"""
Generate a CPIP-style superdataset (no FreeSurfer) with real MRIQC data if available.

Structure:
superdemo/
├── bids/                  (raw BIDS dataset)
├── derivatives/
│   └── fmriprep/          (processed data)
└── qc/
    └── mriqc/             (quality metrics)
"""

from __future__ import annotations
import json, gzip, random, datetime as dt
from pathlib import Path
import typer
import shutil

app = typer.Typer(add_completion=False, no_args_is_help=True)
SESSION_LABELS = ["1a", "2a", "3a", "1b", "2b", "3b"]

# ---------------------------------------------------------------------
# Utility writers
# ---------------------------------------------------------------------
def _writetext(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")

def _writegz(p: Path, payload: str = "placeholder") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wb") as f:
        f.write(payload.encode("utf-8"))

def _should_skip(item: Path) -> bool:
    bad = {"redcap", "logs", ".bids_db", ".git", ".datalad", "__pycache__"}
    return item.name in bad or item.name.startswith(".")

# ---------------------------------------------------------------------
# BIDS dataset writer
# ---------------------------------------------------------------------
def write_bids_tree(bids: Path, n_sub: int, n_ses: int) -> None:
    """Write a minimal BIDS directory with C-PIP session naming (1a, 2a, 3a...)."""
    _writetext(
        bids / "dataset_description.json",
        json.dumps(
            {
                "Name": "Demo BIDS Dataset",
                "BIDSVersion": "1.9.0",
                "DatasetType": "raw",
                "GeneratedBy": [{"Name": "generator", "Version": "0.1"}],
            },
            indent=2,
        ),
    )

    rows = ["participant_id\tage\tsession_count"]
    for i in range(1, n_sub + 1):
        rows.append(f"sub-{i:03d}\t{random.randint(8,17)}\t{n_ses}")
    _writetext(bids / "participants.tsv", "\n".join(rows) + "\n")

    for i in range(1, n_sub + 1):
        sub = f"sub-{i:03d}"
        for ses_idx in range(n_ses):
            ses_label = SESSION_LABELS[ses_idx]
            ses = f"ses-{ses_label}"
            anat = bids / sub / ses / "anat"
            func = bids / sub / ses / "func"
            _writegz(anat / f"{sub}_{ses}_T1w.nii.gz")
            _writetext(anat / f"{sub}_{ses}_T1w.json", json.dumps({"Modality": "MR"}, indent=2))
            _writegz(func / f"{sub}_{ses}_task-rest_bold.nii.gz")
            _writetext(func / f"{sub}_{ses}_task-rest_bold.json", json.dumps({"TaskName": "rest"}, indent=2))

# ---------------------------------------------------------------------
# fMRIPrep derivatives writer
# ---------------------------------------------------------------------
def write_fmriprep_tree(fmriprep: Path, n_sub: int) -> None:
    """Write minimal fMRIPrep derivatives."""
    _writetext(fmriprep / "README", "Demo fMRIPrep derivatives\n")
    for i in range(1, n_sub + 1):
        sub = f"sub-{i:03d}"
        anat = fmriprep / sub / "anat"
        func = fmriprep / sub / "func"
        _writegz(anat / f"{sub}_desc-preproc_T1w.nii.gz")
        _writegz(func / f"{sub}_task-rest_desc-preproc_bold.nii.gz")

# ---------------------------------------------------------------------
# MRIQC copier / generator
# ---------------------------------------------------------------------
def write_mriqc_tree(mriqc: Path, n_sub: int, example_data: Path | None = None, n_ses: int = 1) -> None:
    """Populate MRIQC folder with real example data or synthetic demo placeholders."""

    if example_data and example_data.exists():
        print(f"[INFO] Using real MRIQC example data from: {example_data}")

        # Copy group-level reports once
        for item in example_data.iterdir():
            if _should_skip(item):
                continue
            if item.name.startswith("group_") or item.name == "dataset_description.json":
                shutil.copy2(item, mriqc / item.name)
            elif item.name == "logs":
                shutil.copytree(item, mriqc / "logs", dirs_exist_ok=True)

        # Per subject/session data
        example_subject_dir = example_data / "sub-1723"
        if not example_subject_dir.exists():
            raise FileNotFoundError(f"Expected sub-1723 in {example_data}")

        for i in range(1, n_sub + 1):
            sub_new = f"sub-{i:03d}"
            for ses_idx in range(n_ses):
                ses_label = SESSION_LABELS[ses_idx]
                ses_new = f"ses-{ses_label}"

                dest = mriqc / sub_new
                dest.mkdir(parents=True, exist_ok=True)

                # Copy contents of example subject (but skip hidden stuff)
                for item in example_subject_dir.iterdir():
                    if _should_skip(item):
                        continue
                    target = dest / item.name
                    if item.is_dir():
                        shutil.copytree(item, target, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, target)

                # Rename identifiers recursively
                for path in dest.rglob("*sub-1723*"):
                    new_path = path.with_name(path.name.replace("sub-1723", sub_new))
                    try:
                        path.rename(new_path)
                    except OSError:
                        # Likely exists already (multi-session run) — skip safely
                        pass
                for path in dest.rglob("*ses-1a*"):
                    new_path = path.with_name(path.name.replace("ses-1a", ses_new))
                    try:
                        path.rename(new_path)
                    except OSError:
                        pass

        return

    # ---- fallback synthetic mode ----
    _writetext(mriqc / "README.md", "# MRIQC (demo)\n")
    _writetext(mriqc / "group_T1w.html", "<html>group T1w QC</html>")
    _writetext(mriqc / "group_bold.html", "<html>group BOLD QC</html>")
    for i in range(1, n_sub + 1):
        sub = f"sub-{i:03d}"
        _writetext(
            mriqc / f"{sub}_T1w.json",
            json.dumps(
                {"bids_name": sub, "cjv": round(random.uniform(0.7, 1.1), 3)},
                indent=2,
            ),
        )

# ---------------------------------------------------------------------
# Top README
# ---------------------------------------------------------------------
def write_top_readme(root: Path) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    _writetext(
        root / "README.md",
        f"""# Demo CPIP-Style Superdataset (Minimal)

Generated {ts}.

- `bids/` — BIDS-like raw data
- `derivatives/fmriprep/` — processed data
- `qc/mriqc/` — quality control metrics
"""
    )

# ---------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------
@app.command()
def main(
    root: Path = typer.Option(..., "--root", help="Root of the superdataset"),
    n_sub: int = typer.Option(3, "--n-sub"),
    n_ses: int = typer.Option(1, "--n-ses"),
    force_clean: bool = typer.Option(False, help="Remove existing root"),
    example_data: Path = typer.Option(
        Path("~/local_gitlab/flux-notebooks/data/mriqc_reports_example").expanduser(),
        help="Path to example MRIQC dataset"
    ),
):
    """Create a minimal superdataset (bids + mriqc + fmriprep)."""
    from datalad.api import Dataset

    root = root.resolve()
    if force_clean and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    # Superdataset
    superds = Dataset(root).create()

    # Subdatasets
    bids_ds  = superds.create(path="bids")
    fprep_ds = superds.create(path="derivatives/fmriprep")
    mriqc_ds = superds.create(path="qc/mriqc")

    # Populate
    write_bids_tree(Path(bids_ds.path), n_sub, n_ses)
    write_fmriprep_tree(Path(fprep_ds.path), n_sub)
    write_mriqc_tree(Path(mriqc_ds.path), n_sub, example_data, n_ses)
    write_top_readme(root)

    # Save recursively
    superds.save(message="Initialize superdataset with MRIQC example data", recursive=True)
    print(f"Superdataset ready at: {root}")

# ---------------------------------------------------------------------
if __name__ == "__main__":
    app()
