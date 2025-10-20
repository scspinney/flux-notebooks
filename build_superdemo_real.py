#!/usr/bin/env python3
import os, re, json, shutil
from pathlib import Path
from collections import defaultdict

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
SRC = Path("data/superdemo_real")                   # where demo/montreal, calgary, toronto live
OUT = Path("superdemo_real/bids")    # final BIDS output for Flux
SITE_NAMES = {"montreal": "Montreal", "calgary": "Calgary", "toronto": "Toronto"}

# Reset output
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True, exist_ok=True)

# Regex patterns for parsing folder names
FOLDER_RE = re.compile(
    r"sub_(?P<study>\d+)_ses_(?P<session>[0-9a-zA-Z]+)_fam_(?P<fam>[0-9a-zA-Z\-]+)_site_(?P<site>\d+)",
    re.I,
)
TASK_RE = re.compile(r"_task-(?P<task>[A-Za-z0-9_\-]+)_beh\.(?P<ext>tsv|json)$", re.I)

participants = {}
written = 0

# ─────────────────────────────────────────────
# COPY AND RESTRUCTURE INTO BIDS FORMAT
# ─────────────────────────────────────────────
for site in SITE_NAMES:
    root = SRC / site
    if not root.exists():
        continue
    for folder in root.rglob("sub_*"):
        if not folder.is_dir():
            continue
        m = FOLDER_RE.search(folder.name)
        if not m:
            continue

        study = m.group("study")
        ses = m.group("session")
        fam = m.group("fam")
        site_id = m.group("site")
        site_hr = SITE_NAMES.get(site, site)

        beh_src = folder / "beh"
        if not beh_src.exists():
            continue

        # Create target
        beh_tgt = OUT / f"sub-{study}" / f"ses-{ses}" / "beh"
        beh_tgt.mkdir(parents=True, exist_ok=True)

        # Copy & rename behavioral files
        for f in beh_src.iterdir():
            if not f.is_file():
                continue
            mm = TASK_RE.search(f.name)
            if not mm:
                continue
            task = mm.group("task")
            ext = mm.group("ext").lower()
            new_name = f"sub-{study}_ses-{ses}_task-{task}_beh.{ext}"
            shutil.copy2(f, beh_tgt / new_name)
            written += 1

        # Register participant info
        pid = f"sub-{study}"
        participants[pid] = {
            "participant_id": pid,
            "family_id": "" if fam.lower() in ("nan", "unknown") else fam,
            "site_id": site_id,
            "site_name": site_hr,
        }

print(f"Copied {written} files from demo/* → {OUT}")

# ─────────────────────────────────────────────
# BUILD participants.tsv / JSON
# ─────────────────────────────────────────────
tsv_path = OUT / "participants.tsv"
with tsv_path.open("w", encoding="utf-8") as f:
    f.write("participant_id\tfamily_id\tsite_id\tsite_name\n")
    for p in sorted(participants.keys()):
        row = participants[p]
        f.write(
            f"{row['participant_id']}\t{row['family_id']}\t{row['site_id']}\t{row['site_name']}\n"
        )

(OUT / "participants.json").write_text(
    json.dumps(
        {
            "participant_id": {"Description": "BIDS subject identifier"},
            "family_id": {"Description": "Family linkage identifier"},
            "site_id": {"Description": "Site code (1644=Montreal, 1643=Calgary, 1645=Toronto)"},
            "site_name": {"Description": "Human-readable site name"},
        },
        indent=2,
    )
)

# ─────────────────────────────────────────────
# BUILD dataset_description.json
# ─────────────────────────────────────────────
(OUT / "dataset_description.json").write_text(
    json.dumps(
        {
            "Name": "SuperDemo Real Dataset",
            "BIDSVersion": "1.8.0",
            "DatasetType": "raw",
            "Authors": ["Sean Spinney", "C-PIP Team"],
            "GeneratedBy": [
                {"Name": "convert_demo.py", "Version": "1.0"},
                {"Name": "build_superdemo_real.py", "Version": "1.0"},
            ],
            "Acknowledgements": "Synthetic behavioral dataset for Flux demonstration.",
        },
        indent=2,
    )
)

print(f"✅ Wrote participants.tsv and dataset_description.json to {OUT}")
print("Structure preview:\n")
os.system(f"tree {OUT} -L 3")
