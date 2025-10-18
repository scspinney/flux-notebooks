#!/usr/bin/env python3
from __future__ import annotations
import json, random, datetime as dt, shutil, re, sys, hashlib, os, stat
from pathlib import Path
import gzip
import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)

# -------------------- helpers --------------------

def _say(msg: str) -> None:
    print(msg, flush=True)

def _writetext(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")

def _writegz(p: Path, payload: str = "placeholder") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wb") as f:
        f.write(payload.encode("utf-8"))

def _safe_rmtree(path: Path) -> None:
    """rm -rf that also fixes read-only annex files."""
    def onerror(func, pth, exc_info):
        try:
            os.chmod(pth, stat.S_IWUSR | stat.S_IREAD)
            func(pth)
        except Exception as e:
            _say(f"[WARN] Could not remove {pth}: {e}")
    shutil.rmtree(path, onerror=onerror)

# -------------------- BIDS tree --------------------

def write_bids_tree(bids: Path, n_sub: int, n_ses: int) -> None:
    _writetext(
        bids / "dataset_description.json",
        json.dumps(
            {
                "Name": "Demo Superdataset",
                "BIDSVersion": "1.9.0",
                "DatasetType": "raw",
                "GeneratedBy": [{"Name": "generator", "Version": "3.1-enforce-copy"}],
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
        for j in range(1, n_ses + 1):
            ses = f"ses-{j:02d}"
            anat = bids / sub / ses / "anat"
            func = bids / sub / ses / "func"
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

# -------------------- MRIQC: COPY ONLY TOP-LEVEL HTMLs --------------------

def precopy_mriqc_htmls(mriqc_dir: Path, n_sub: int, n_ses: int, example_data: Path) -> None:
    _say(f"[INFO] Using real MRIQC example data from: {example_data}")
    if not example_data.exists():
        raise FileNotFoundError(f"Example MRIQC data not found at: {example_data}")

    # demo group pages (also .html at depth 1)
    _writetext(mriqc_dir / "README.md", "# MRIQC (demo)\n\nCopied and renamed from real example outputs.\n")
    _writetext(mriqc_dir / "group_T1w.html", "<html><body><h2>Group T1w QC (demo)</h2></body></html>")
    _writetext(mriqc_dir / "group_bold.html", "<html><body><h2>Group BOLD QC (demo)</h2></body></html>")

    # exactly the six top-level HTMLs
    src_htmls = sorted([p for p in example_data.iterdir() if p.suffix.lower() == ".html"])
    _say(f"[DEBUG] Source HTMLs at example root: {len(src_htmls)}")
    for p in src_htmls:
        _say(f"        src: {p.name}")
    if not src_htmls:
        raise SystemExit("[FATAL] No .html files at example_data root — expected 6.")

    # tokens from filename (e.g., sub-1723_ses-1a_*.html)
    sample = src_htmls[0].name
    m_sub = re.search(r"(sub-\d+)", sample)
    m_ses = re.search(r"(ses-\d+[a-z])", sample)
    src_sub_token = m_sub.group(1) if m_sub else "sub-000"
    src_ses_token = m_ses.group(1) if m_ses else "ses-1a"
    _say(f"[DEBUG] Renaming tokens: sub={src_sub_token!r}  ses={src_ses_token!r}")

    copied = []
    for i in range(1, n_sub + 1):
        sub_new = f"sub-{i:03d}"
        dest_dir = mriqc_dir / sub_new
        dest_dir.mkdir(parents=True, exist_ok=True)
        for j in range(1, n_ses + 1):
            ses_new = f"ses-{j}a"  # mirror 1a, 2a, …
            for src in src_htmls:
                new_name = src.name.replace(src_sub_token, sub_new).replace(src_ses_token, ses_new)
                dst = dest_dir / new_name
                # Write bytes (bypasses any oddities with copy flags)
                dst.write_bytes(src.read_bytes())
                # Patch identifiers inside HTML
                try:
                    txt = dst.read_text(errors="ignore")
                    txt = txt.replace(src_sub_token, sub_new).replace(src_ses_token, ses_new)
                    dst.write_text(txt, encoding="utf-8")
                except Exception as e:
                    _say(f"[WARN] Could not patch identifiers in {dst}: {e}")
                _say(f"[COPY] {src.name} -> {dst.relative_to(mriqc_dir)}")
                copied.append(dst)

    # manifest & assert
    manifest = mriqc_dir / "_COPIED_HTMLS.txt"
    _writetext(manifest, "HTML files copied:\n" + "\n".join(str(p.relative_to(mriqc_dir)) for p in copied) + "\n")
    _say(f"[INFO] Manifest: {manifest}")

    found = list(mriqc_dir.rglob("*.html"))
    _say(f"[CHECK] HTMLs present in qc/mriqc BEFORE DataLad: {len(found)}")
    for p in sorted(found):
        rel = p.relative_to(mriqc_dir)
        if len(rel.parts) <= 2:
            _say(f"   [FOUND] {rel}")
    if not found:
        raise SystemExit("[FATAL] No HTMLs in qc/mriqc before DataLad — stopping.")

# -------------------- fMRIPrep dummy tree --------------------

def write_fmriprep_tree(fs: Path, n_sub: int) -> None:
    _writetext(fs / "README", "Demo fMRIPrep derivatives (placeholder)\n")
    for i in range(1, n_sub + 1):
        sub = f"sub-{i:03d}"
        (fs / sub / "anat").mkdir(parents=True, exist_ok=True)
        (fs / sub / "func").mkdir(parents=True, exist_ok=True)
        (fs / sub / "anat" / f"{sub}_desc-preproc_T1w.nii.gz").write_bytes(b"")
        (fs / sub / "func" / f"{sub}_task-rest_desc-preproc_bold.nii.gz").write_bytes(b"")

# -------------------- Top-level --------------------

def write_top_readme(root: Path) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    _writetext(
        root / "README.md",
        f"""# Demo Neuroimaging Superdataset

Generated {ts}.

- `bids/` — BIDS-like raw placeholders  
- `qc/mriqc/` — MRIQC example HTMLs (copied + renamed per subject/session)  
- `derivatives/fmriprep/` — fMRIPrep demo outputs

All MRIQC assets stored as normal files (non-annexed) for direct dashboard access.
"""
    )

# -------------------- main --------------------

@app.command()
def main(
    root: Path = typer.Option(..., "--root", help="Where to create the superdataset"),
    example_data: Path = typer.Option("data/mriqc_reports_example", "--example-data", help="Path to example MRIQC data"),
    n_sub: int = typer.Option(3, "--n-sub", min=1),
    n_ses: int = typer.Option(1, "--n-ses", min=1),
    force_clean: bool = typer.Option(False, help="rm -rf ROOT first"),
):
    # Identity banner (helps verify you are running this exact file)
    here = Path(__file__).resolve()
    sha = hashlib.sha256(here.read_bytes()).hexdigest()
    _say(f"[START] Running: {here}")
    _say(f"[START] SHA256:  {sha}")

    root = root.resolve()
    if force_clean and root.exists():
        _say(f"[CLEAN] Removing previous tree: {root}")
        _safe_rmtree(root)

    # Build plain directories and copy HTMLs BEFORE any DataLad
    (root / "bids").mkdir(parents=True, exist_ok=True)
    (root / "qc" / "mriqc").mkdir(parents=True, exist_ok=True)
    (root / "derivatives" / "fmriprep").mkdir(parents=True, exist_ok=True)

    write_bids_tree(root / "bids", n_sub, n_ses)
    precopy_mriqc_htmls(root / "qc" / "mriqc", n_sub, n_ses, example_data)
    write_fmriprep_tree(root / "derivatives" / "fmriprep", n_sub)
    write_top_readme(root)

    # Assert again before DataLad
    pre_html_count = sum(1 for _ in (root / "qc" / "mriqc").rglob("*.html"))
    _say(f"[ASSERT] On-disk HTMLs before DataLad init: {pre_html_count}")
    if pre_html_count == 0:
        raise SystemExit("[FATAL] No HTMLs on disk in qc/mriqc — aborting before DataLad.")

    # Now wrap with DataLad (qc/mriqc as plain Git)
    from datalad.api import Dataset
    superds = Dataset(root).create()
    superds.create(path="bids")
    superds.create(path="qc/mriqc", annex=False)
    superds.create(path="derivatives/fmriprep")
    superds.save(message="Initialize demo superdataset with MRIQC HTMLs (precopied)", recursive=True)

    # Verify after save
    post_html_count = sum(1 for _ in (root / "qc" / "mriqc").rglob("*.html"))
    _say(f"[CHECK] HTMLs present in qc/mriqc after save: {post_html_count}")
    if post_html_count == 0:
        _say("[FATAL] HTMLs disappeared after save — check .gitattributes/annex settings.")
        sys.exit(3)

    _say(f"\nSuperdataset ready at: {root}")
    _say(f"→ MRIQC example data imported from: {example_data}")

if __name__ == "__main__":
    app()
