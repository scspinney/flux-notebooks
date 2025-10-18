from pathlib import Path
import pandas as pd
from bids import BIDSLayout

# ------------------------------------------------------------
# Target totals per site (update if recruitment goals change)
# ------------------------------------------------------------
TARGET_TOTALS = {
    "Calgary": 263,
    "Montreal": 263,
    "Toronto": 263,
}

SITE_MAP = {
    "calgary": "Calgary",
    "montreal": "Montreal",
    "toronto": "Toronto",
    "sickkids": "Toronto",
}


# ------------------------------------------------------------
# Helper: determine if a subject has completed all pipelines
# ------------------------------------------------------------
def is_preprocessed_all(sub_id: str, derivatives_root: Path) -> bool:
    """
    Strict definition: subject must have final outputs from all pipelines
    (MRIQC, fMRIPrep, and FreeSurfer).
    """
    sub_id = sub_id.replace("sub-", "")
    ok_mriqc = False
    ok_fmriprep = False
    ok_freesurfer = False

    # MRIQC check
    mriqc_path = derivatives_root / "mriqc" / f"sub-{sub_id}"
    if any(mriqc_path.glob("**/*.html")) or any(mriqc_path.glob("**/*.json")):
        ok_mriqc = True

    # fMRIPrep check
    fmriprep_path = derivatives_root / "fmriprep" / f"sub-{sub_id}"
    if any(fmriprep_path.glob("**/*.html")) or any(fmriprep_path.glob("**/*confounds_timeseries.tsv")):
        ok_fmriprep = True

    # FreeSurfer check
    fs_path = derivatives_root / "freesurfer" / f"sub-{sub_id}"
    if (fs_path / "stats").exists() and (fs_path / "surf").exists():
        ok_freesurfer = True

    return ok_mriqc and ok_fmriprep and ok_freesurfer


# ------------------------------------------------------------
# Helper: extract all subject IDs from a REDCap CSV
# ------------------------------------------------------------
def extract_subject_ids(csv_file: Path):
    df = pd.read_csv(csv_file, low_memory=False)
    if "record_id" not in df.columns:
        return []
    return [str(x) for x in df["record_id"].dropna().unique()]


# ------------------------------------------------------------
# Per-site summarizer
# ------------------------------------------------------------
def summarize_targets(redcap_csv: Path):
    """Compute observed recruitment vs study targets for each site."""
    df = pd.read_csv(redcap_csv, low_memory=False)
    site_col = next(
        (
            c
            for c in df.columns
            if c.lower()
            in ["site", "site_name", "study_site", "location", "recruitment_site"]
        ),
        None,
    )

    # --- Try to find site info ---
    if site_col:
        df["site"] = df[site_col]
        site_name = str(df["site"].dropna().unique()[0]).strip().capitalize()
    else:
        # --- fallback: infer from filename ---
        site_name = next(
            (v for k, v in SITE_MAP.items() if k in redcap_csv.name.lower()),
            None,
        )
        if site_name is None:
            raise ValueError(
                f"Could not determine site for {redcap_csv.name}. Columns: {list(df.columns)[:10]} ..."
            )

    obs = len(df["record_id"].unique())
    tgt = TARGET_TOTALS.get(site_name, 0)
    pct = round(100 * obs / tgt, 1) if tgt > 0 else 0

    return {
        "sites": {site_name: {"observed": obs, "target": tgt, "percent": pct}},
        "overall": pct,
        "total_observed": obs,
        "total_target": tgt,
    }


# ------------------------------------------------------------
# Combined summary across all sites
# ------------------------------------------------------------
def summarize_all_sites(
    redcap_dir: Path = Path("data/redcap"),
    derivatives_root: Path = Path("data/derivatives")
):
    """
    Merge and summarize all available REDCap exports in `redcap_dir`,
    and compute preprocessing completion from `derivatives_root`.
    """
    redcap_dir = Path(redcap_dir)
    derivatives_root = Path(derivatives_root)
    csvs = sorted(redcap_dir.glob("*.csv"))
    if not csvs:
        raise FileNotFoundError(f"No REDCap CSVs found in {redcap_dir}")

    all_sites = {}
    total_obs, total_tgt, total_proc = 0, 0, 0

    for csv in csvs:
        try:
            res = summarize_targets(csv)
            for site, vals in res["sites"].items():
                sub_ids = extract_subject_ids(csv)
                processed_count = sum(
                    is_preprocessed_all(sub, derivatives_root) for sub in sub_ids
                )
                vals["processed"] = processed_count
                vals["processed_percent"] = (
                    round(100 * processed_count / vals["target"], 1)
                    if vals["target"] > 0
                    else 0
                )

                all_sites[site] = vals
                total_obs += vals["observed"]
                total_tgt += vals["target"]
                total_proc += processed_count
        except Exception as e:
            print(f"⚠️ Skipping {csv.name}: {e}")

    overall = round(100 * total_obs / total_tgt, 1) if total_tgt > 0 else 0
    overall_proc = round(100 * total_proc / total_tgt, 1) if total_tgt > 0 else 0

    # Fill missing sites
    for site, tgt in TARGET_TOTALS.items():
        if site not in all_sites:
            all_sites[site] = {
                "observed": 0,
                "target": tgt,
                "percent": 0.0,
                "processed": 0,
                "processed_percent": 0.0,
            }

    return {
        "sites": all_sites,
        "overall": overall,
        "overall_processed": overall_proc,
        "total_observed": total_obs,
        "total_processed": total_proc,
        "total_target": total_tgt,
    }


# ------------------------------------------------------------
# PyBIDS-based modality summary
# ------------------------------------------------------------


def summarize_modalities(bids_root: Path = Path("data/superdemo_real/bids"),
                         derivatives_root: Path = Path("data/derivatives")):
    """
    Use PyBIDS to summarize available modalities and preprocessing status
    across the dataset.

    Returns a dict suitable for Dash display, e.g.:
    {
        "modalities": [
            {"name": "T1w", "available": 87, "processed": 75, "percent": 86.2},
            {"name": "BOLD", "available": 84, "processed": 69, "percent": 82.1},
            {"name": "DWI", "available": 22, "processed": 18, "percent": 81.8},
        ]
    }
    """

    # Initialize BIDS layout for raw data
    layout = BIDSLayout(bids_root, validate=False, derivatives=False)
    subjects = layout.get_subjects()

    # Identify modalities present in the dataset
    modality_types = ["T1w", "T2w", "bold", "dwi"]
    mod_counts = {m: 0 for m in modality_types}
    preproc_counts = {m: 0 for m in modality_types}

    # Count available modalities
    for subj in subjects:
        subj_files = layout.get(subject=subj, suffix=modality_types, extension=[".nii", ".nii.gz"])
        suffixes = {f.entities.get("suffix") for f in subj_files}
        for mod in modality_types:
            if mod.lower() in [s.lower() for s in suffixes if s]:
                mod_counts[mod] += 1

    # Now check derivatives to count how many are preprocessed
    deriv_paths = [p for p in derivatives_root.glob("*") if p.is_dir()]
    for deriv in deriv_paths:
        try:
            deriv_layout = BIDSLayout(deriv, validate=False, derivatives=True)
            deriv_subjects = deriv_layout.get_subjects()
            for mod in modality_types:
                for subj in deriv_subjects:
                    files = deriv_layout.get(subject=subj, suffix=mod.lower(), extension=[".nii", ".nii.gz"])
                    if files:
                        preproc_counts[mod] += 1
        except Exception:
            continue  # skip non-BIDS derivatives (some may not validate cleanly)

    # Build output summary
    summary = []
    for mod in modality_types:
        available = mod_counts[mod]
        processed = preproc_counts[mod]
        pct = round(100 * processed / available, 1) if available > 0 else 0
        summary.append({
            "name": mod.upper(),
            "available": available,
            "processed": processed,
            "percent": pct
        })

    return {"modalities": summary}

