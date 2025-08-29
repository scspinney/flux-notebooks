#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


def find_subdatasets(super_root: Path) -> List[Path]:
    """Return paths to subdatasets. Prefer DataLad; fallback to immediate subdirs that look like BIDS."""
    try:
        from datalad.api import Dataset  # type: ignore
        ds = Dataset(str(super_root))
        subs = ds.subdatasets(return_type="path", recursive=False)
        return [Path(p) for p in subs]
    except Exception:
        out: List[Path] = []
        for p in super_root.iterdir():
            if p.is_dir() and (p / "dataset_description.json").exists():
                out.append(p)
        return sorted(out)


def _slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "dataset"


def dataset_slug(ds_path: Path) -> str:
    meta = ds_path / "dataset_description.json"
    if meta.exists():
        try:
            name = json.loads(meta.read_text()).get("Name")
            if name:
                return _slugify(name)
        except Exception:
            pass
    return _slugify(ds_path.name)


def dataset_title(ds_path: Path) -> str:
    meta = ds_path / "dataset_description.json"
    if meta.exists():
        try:
            name = json.loads(meta.read_text()).get("Name")
            if name:
                return name
        except Exception:
            pass
    return ds_path.name


def run(cmd: list[str], cwd: Optional[Path] = None) -> None:
    print(">>", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)

def write_config(
    book_root: Path,
    execute_mode: str = "off",            # off | auto | force (we pre-execute)
    repo_url: str | None = None,
    repo_branch: str = "main",
    path_to_book: str = "book",
    binderhub_url: str = "https://mybinder.org",
) -> None:
    """
    Jupyter Book config that enables 'Live Code' via Thebe and
    points both Binder and Thebe to the same repo/branch/path.
    """
    repo_block = ""
    if repo_url:
        repo_block = f"""
repository:
  url: {repo_url}
  branch: {repo_branch}
  path_to_book: {path_to_book}
"""
    cfg = f"""# Jupyter Book config for flux-notebooks
title: Flux Notebooks — Datasets
only_build_toc_files: true

execute:
  execute_notebooks: "{execute_mode}"
  timeout: 900
  allow_errors: false
  stderr_output: "show"
  exclude_patterns:
    - "**/.ipynb_checkpoints/**"

launch_buttons:
  binderhub_url: {binderhub_url}

thebe: true
thebe_config:
  binderhub_url: {binderhub_url}
  repository_url: {repo_url if repo_url else ""}
  repository_branch: {repo_branch}
  path_to_docs: {path_to_book}
  kernel_name: python3

html:
  use_repository_button: false
  use_issues_button: false
  use_edit_page_button: false
  navbar_number_sections: false
  baseurl: ""

sphinx:
  config:
    # Prefer embedded widget views if present
    nb_mime_priority_overrides:
      - when: html
        preference:
          - application/vnd.jupyter.widget-view+json
          - text/html
          - image/svg+xml
          - image/png
          - text/plain
    html_show_sourcelink: false
    html_show_copyright: false
{repo_block}"""
    (book_root / "_config.yml").write_text(cfg)


def write_binder_env(book_root: Path) -> None:
    """
    Create a minimal Binder env so Thebe kernels have ipywidgets + friends.
    Binder looks first in ./binder/, then repo root.
    """
    bdir = book_root / "binder"
    bdir.mkdir(parents=True, exist_ok=True)
    req = bdir / "requirements.txt"
    if not req.exists():
        req.write_text(
            "\n".join(
                [
                    "ipywidgets>=8",
                    "pandas",
                    "numpy",
                    "matplotlib",
                    "seaborn",
                    "pybids>=0.16",
                    # add any extras your notebooks need:
                    # "nibabel", "scipy", "plotly", ...
                ]
            )
            + "\n"
        )


def write_intro(book_root: Path, entries: List[Tuple[str, str]]) -> None:
    intro = book_root / "intro.md"
    lines = [
        "# Flux Notebooks — Superdataset overview\n",
        "This book aggregates one report notebook per dataset.\n",
        "",
        "## Datasets",
        "",
    ]
    if not entries:
        lines.append("_No datasets found._")
    else:
        for title, slug in entries:
            lines.append(f"- [{title}](datasets/{slug}/bids_summary.ipynb)")
    intro.write_text("\n".join(lines) + "\n")


def _yaml_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_toc(book_root: Path, entries: List[Tuple[str, str]]) -> None:
    toc = book_root / "_toc.yml"
    lines = ["format: jb-book", "root: intro", "chapters:"]
    for title, slug in entries:
        lines.append(f"  - file: datasets/{slug}/bids_summary")
        lines.append(f"    title: {_yaml_quote(title)}")
    toc.write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a Jupyter Book tying notebooks per dataset.")
    ap.add_argument("--super", dest="super_root", required=True, help="Path to superdataset root")
    ap.add_argument("--book", dest="book_root", default="book", help="Output book directory")
    # Repo metadata so Binder/Thebe can launch a kernel for widgets
    ap.add_argument("--repo-url", default="", help="Repository URL hosting the book (for Binder)")
    ap.add_argument("--repo-branch", default="main", help="Repository branch (for Binder)")
    ap.add_argument("--path-to-book", default="book", help="Path to book within the repo (for Binder)")
    args = ap.parse_args()

    super_root = Path(args.super_root).resolve()
    book_root = Path(args.book_root).resolve()
    book_ds_dir = book_root / "datasets"
    book_ds_dir.mkdir(parents=True, exist_ok=True)

    # 1) discover datasets
    datasets = find_subdatasets(super_root)
    if not datasets and (super_root / "dataset_description.json").exists():
        datasets = [super_root]

    # 2) generate notebooks with flux-notebooks
    toc_entries: List[Tuple[str, str]] = []
    for ds in datasets:
        slug = dataset_slug(ds)
        title = dataset_title(ds)
        outdir = book_ds_dir / slug
        if outdir.exists():
            shutil.rmtree(outdir)
        outdir.mkdir(parents=True, exist_ok=True)

        run(["flux-notebooks", "--dataset", str(ds), "--outdir", str(outdir)])
        nb = outdir / "bids_summary.ipynb"
        if not nb.exists():
            raise RuntimeError(f"Notebook not produced for {ds}")
        toc_entries.append((title, slug))

    # 3) scaffold book config/TOC/intro + Binder env
    write_config(
        book_root,
        execute_mode="off",  # we already saved outputs; Thebe is for live editing
        repo_url=args.repo_url,
        repo_branch=args.repo_branch or "main",
        path_to_book=args.path_to_book or "book",
    )

    write_binder_env(book_root)
    write_intro(book_root, toc_entries)
    write_toc(book_root, toc_entries)

    # 4) build the book
    run(["jupyter-book", "build", str(book_root)])
    print(f"\n✔ Built book → {book_root / '_build' / 'html'}")
    print("   Tip: push this folder to the repo you passed in --repo-url so Binder can launch kernels.")
    print("   In the built HTML, click the rocket ▶ ‘Live Code’ to start Thebe, then your widgets will compute.")


if __name__ == "__main__":
    main()
