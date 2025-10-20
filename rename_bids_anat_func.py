#!/usr/bin/env python3
import shutil
from pathlib import Path

# --------------------------------------------
# CONFIGURATION
# --------------------------------------------

# Root where the MRIQC data lives
# Run from ~/local_gitlab/flux-notebooks
ROOT = Path("superdemo_real/qc/mriqc")

# Template subject to copy from
TEMPLATE_SUB = "sub-001"

# Subjects you want to generate
NEW_SUBJECTS = [
    "sub-1359", "sub-1524", "sub-1676", "sub-1760", "sub-1920",
    "sub-1987", "sub-2117", "sub-2135"
]

# --------------------------------------------
# UTILITIES
# --------------------------------------------

def replace_subject_in_file(file_path: Path, old_sub: str, new_sub: str):
    """Replace subject ID inside a single file (HTML, JSON, TSV, etc.)."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return  # skip binary or unreadable files
    if old_sub in text:
        file_path.write_text(text.replace(old_sub, new_sub), encoding="utf-8")

def replace_subject_everywhere(sub_dir: Path, old_sub: str, new_sub: str):
    """Recursively replace subject IDs in all text-based files."""
    for ext in ("*.html", "*.json", "*.tsv"):
        for file_path in sub_dir.rglob(ext):
            replace_subject_in_file(file_path, old_sub, new_sub)

def rename_files_and_dirs(sub_dir: Path, old_sub: str, new_sub: str):
    """Recursively rename all files and directories containing old subject name."""
    # Rename files first (deepest first)
    for path in sorted(sub_dir.rglob(f"*{old_sub}*"), key=lambda p: len(str(p)), reverse=True):
        new_name = path.name.replace(old_sub, new_sub)
        new_path = path.with_name(new_name)
        path.rename(new_path)

# --------------------------------------------
# MAIN LOGIC
# --------------------------------------------

template_dir = ROOT / TEMPLATE_SUB
if not template_dir.exists():
    raise FileNotFoundError(f"Template folder not found: {template_dir}")

print(f"Using {TEMPLATE_SUB} as template")

for new_sub in NEW_SUBJECTS:
    dest_dir = ROOT / new_sub
    if dest_dir.exists():
        print(f"⚠️  Skipping {new_sub} (already exists)")
        continue

    print(f"→ Creating {new_sub}")
    shutil.copytree(template_dir, dest_dir, dirs_exist_ok=True)

    # Rename files/directories and update HTML references
    rename_files_and_dirs(dest_dir, TEMPLATE_SUB, new_sub)
    replace_subject_everywhere(dest_dir, TEMPLATE_SUB, new_sub)

    print(f"✅ Finished {new_sub}")

print("\n🎯 All subjects cloned successfully.")













# #!/usr/bin/env python3
# import os
# import shutil
# from pathlib import Path

# # ─────────────────────────────────────────────
# # CONFIGURATION
# # ─────────────────────────────────────────────
# ROOT = Path("superdemo_real/derivatives/fmriprep")
# TEMPLATE = ROOT / "sub-001"

# # List of new subjects to create
# NEW_SUBJECTS = [
#     "sub-1359", "sub-1681", "sub-1760",
#     "sub-2877", "sub-2959", "sub-2977",
#     "sub-3629", "sub-3729"
# ]

# # ─────────────────────────────────────────────
# # VALIDATE TEMPLATE
# # ─────────────────────────────────────────────
# if not TEMPLATE.exists():
#     raise FileNotFoundError(f"Template folder not found: {TEMPLATE}")

# print(f"Using {TEMPLATE} as template for {len(NEW_SUBJECTS)} subjects")

# # ─────────────────────────────────────────────
# # CLONE STRUCTURE
# # ─────────────────────────────────────────────
# for subj in NEW_SUBJECTS:
#     dest = ROOT / subj
#     if dest.exists():
#         print(f"⚠️  Skipping existing {dest}")
#         continue

#     # Copy directory structure (no content yet)
#     shutil.copytree(TEMPLATE, dest, symlinks=True)
#     print(f"→ Created {dest}")

#     # Walk through and rename any file or symlink with 'sub-001'
#     for f in dest.rglob("*"):
#         if not f.is_file():
#             continue

#         old_name = f.name
#         if "sub-001" in old_name:
#             new_name = old_name.replace("sub-001", subj)
#             new_path = f.with_name(new_name)

#             if f.is_symlink():
#                 target = os.readlink(f)
#                 f.unlink()
#                 new_path.symlink_to(target)
#             else:
#                 f.rename(new_path)

#             print(f"  Renamed: {old_name} → {new_name}")

# print("\n✅ All derivative subfolders created and renamed successfully.")










# #!/usr/bin/env python3
# import os
# from pathlib import Path
# import re
# import subprocess

# ROOT = Path("superdemo_real/bids")  # adjust if running elsewhere
# n_renamed = 0

# for subj_dir in sorted(ROOT.glob("sub-*")):
#     if not subj_dir.is_dir():
#         continue
#     subj = subj_dir.name  # e.g. sub-1359

#     for ses_dir in subj_dir.glob("ses-*"):
#         for mod in ("anat", "func"):
#             mod_dir = ses_dir / mod
#             if not mod_dir.exists():
#                 continue

#             for f in mod_dir.iterdir():
#                 if not f.is_file():
#                     continue

#                 # Match the incorrect prefix (e.g., sub-001_...)
#                 m = re.match(r"sub-(\d+)_ses-(\w+)_.*", f.name)
#                 if not m:
#                     continue

#                 old_sub = f"sub-{m.group(1)}"
#                 if old_sub == subj:
#                     continue  # already correct

#                 new_name = f.name.replace(old_sub, subj)
#                 new_path = f.with_name(new_name)

#                 # Preserve symlink vs file
#                 if f.is_symlink():
#                     target = os.readlink(f)
#                     f.unlink()
#                     new_path.symlink_to(target)
#                 else:
#                     f.rename(new_path)

#                 print(f"Renamed: {f} -> {new_path}")
#                 n_renamed += 1

# print(f"\n✅ Done. Renamed {n_renamed} files under {ROOT}")
