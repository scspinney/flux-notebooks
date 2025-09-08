#!/usr/bin/env python3
"""
Create a demo neuroimaging superdataset with DataLad (pure Python API):

<root>/
  bids/                      (subdataset)
    dataset_description.json
    participants.tsv
    sub-XX/ses-YY/anat/*.nii.gz (tiny gz placeholders)
    sub-XX/ses-YY/func/*.nii.gz + sidecars
  qa/mriqc/                  (subdataset)
    group_T1w.html, group_bold.html, sub-XX_T1w.json
  derivatives/freesurfer/    (subdataset)
    sub-XX/surf/{lh.white,rh.white}, stats/aseg.stats
  README.md

This follows the DataLad docs flow:
- Create superdataset
- Create subdatasets from the superdataset with Dataset.create()
- Write content
- superds.save(..., recursive=True)

Usage:
  python examples/generate_super_dataset_datalad.py --root ./superdemo --n-sub 3 --n-ses 2
"""

from __future__ import annotations
import json, gzip, random, datetime as dt
from pathlib import Path
import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)

def _writetext(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")

def _writegz(p: Path, payload: str = "placeholder") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wb") as f:
        f.write(payload.encode("utf-8"))

def write_bids_tree(bids: Path, n_sub: int, n_ses: int) -> None:
    _writetext(
        bids / "dataset_description.json",
        json.dumps(
            {
                "Name": "Demo Superdataset",
                "BIDSVersion": "1.9.0",
                "DatasetType": "raw",
                "GeneratedBy": [{"Name": "generator", "Version": "0.1"}],
            },
            indent=2,
        ),
    )
    rows = ["participant_id\tage\tsession_count"]
    for i in range(1, n_sub + 1):
        rows.append(f"sub-{i:02d}\t{random.randint(8,17)}\t{n_ses}")
    _writetext(bids / "participants.tsv", "\n".join(rows) + "\n")

    for i in range(1, n_sub + 1):
        sub = f"sub-{i:02d}"
        for j in range(1, n_ses + 1):
            ses = f"ses-{j:02d}"
            anat = bids / sub / ses / "anat"
            func = bids / sub / ses / "func"
            # Tiny “nii.gz” payloads (just gzipped text) to populate the tree
            _writegz(anat / f"{sub}_{ses}_T1w.nii.gz", "NIfTI placeholder")
            _writetext(
                anat / f"{sub}_{ses}_T1w.json",
                json.dumps(
                    {"Modality": "MR", "MagneticFieldStrength": 3, "RepetitionTime": 2.3, "EchoTime": 0.003},
                    indent=2,
                ),
            )
            task = "rest"
            _writegz(func / f"{sub}_{ses}_task-{task}_bold.nii.gz", "NIfTI placeholder")
            _writetext(
                func / f"{sub}_{ses}_task-{task}_bold.json",
                json.dumps({"TaskName": task, "RepetitionTime": 2.0}, indent=2),
            )
            _writetext(func / f"{sub}_{ses}_task-{task}_events.tsv", "onset\tduration\ttrial_type\n")

def write_mriqc_tree(mriqc: Path, n_sub: int) -> None:
    _writetext(mriqc / "README.md", "# MRIQC (demo)\n\nGroup/subject placeholders.\n")
    _writetext(mriqc / "group_T1w.html", "<html><body>group T1w QC (demo)</body></html>")
    _writetext(mriqc / "group_bold.html", "<html><body>group BOLD QC (demo)</body></html>")
    for i in range(1, min(n_sub, 3) + 1):
        sub = f"sub-{i:02d}"
        _writetext(mriqc / f"{sub}_T1w.json", json.dumps({"bids_name": sub, "cjv": round(random.uniform(0.7,1.1),3)}, indent=2))

def write_freesurfer_tree(fs: Path, n_sub: int) -> None:
    _writetext(fs / "README", "Demo FreeSurfer derivatives (placeholder)\n")
    for i in range(1, n_sub + 1):
        sub = f"sub-{i:02d}"
        (fs / sub / "surf").mkdir(parents=True, exist_ok=True)
        (fs / sub / "surf" / "lh.white").write_bytes(b"")
        (fs / sub / "surf" / "rh.white").write_bytes(b"")
        _writetext(fs / sub / "stats" / "aseg.stats", "# demo aseg stats\n")

def write_top_readme(root: Path) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    _writetext(
        root / "README.md",
        f"""# Demo Neuroimaging Superdataset

Generated {ts}.

- `bids/` — BIDS-like raw placeholders
- `qa/mriqc/` — MRIQC demo artifacts
- `derivatives/freesurfer/` — FreeSurfer demo outputs

Synthetic demo for pipelines & docs.
""",
    )

@app.command()
def main(
    root: Path = typer.Option(..., "--root", help="Where to create the superdataset"),
    n_sub: int = typer.Option(3, "--n-sub", min=1),
    n_ses: int = typer.Option(1, "--n-ses", min=1),
    force_clean: bool = typer.Option(False, help="rm -rf ROOT first"),
):
    # Import here so the script fails clearly if DataLad is missing.
    from datalad.api import Dataset

    root = root.resolve()
    if force_clean and root.exists():
        import shutil
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    # 1) Superdataset (docs pattern)
    superds = Dataset(root).create()  # equivalent to `datalad create <root>`

    # 2) Subdatasets from the superdataset (docs: `datalad create -d . sub1`)
    bids_ds  = superds.create(path="bids")
    mriqc_ds = superds.create(path="qa/mriqc")
    fs_ds    = superds.create(path="derivatives/freesurfer")

    # 3) Write content into the *working trees* of each subdataset
    write_bids_tree(Path(bids_ds.path), n_sub, n_ses)
    write_mriqc_tree(Path(mriqc_ds.path), n_sub)
    write_freesurfer_tree(Path(fs_ds.path), n_sub)
    write_top_readme(root)

    # 4) Single recursive save up the tree (docs demonstrate this behavior)
    superds.save(message="Initialize demo superdataset with subdatasets and content", recursive=True)

    print(f"Superdataset ready at: {root}")
    print("Try:")
    print(f"  cd {root}")
    print("  datalad subdatasets")
    print("  datalad diff -r --report-untracked all")

if __name__ == "__main__":
    app()
