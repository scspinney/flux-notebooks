# src/flux_notebooks/superbuilder.py
from __future__ import annotations
import shutil, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
from jinja2 import Environment, FileSystemLoader

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)

def discover_all_datasets(super_root: Path, max_depth: int = 3) -> list[Path]:
    """
    Use DataLad to enumerate the superdataset root and all registered subdatasets.
    Depth is measured relative to super_root.
    """
    try:
        from datalad.api import Dataset
    except ImportError:
        typer.secho("datalad is required for discovery, but not importable.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    super_root = super_root.resolve()
    ds = Dataset(super_root)
    if not ds.is_installed():
        typer.secho(f"Path is not an installed DataLad dataset: {super_root}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    cand_paths = [Path(ds.path).resolve()]
    sub_paths = ds.subdatasets(recursive=True, result_xfm="paths") or []
    cand_paths.extend(Path(p).resolve() for p in sub_paths)

    out: list[Path] = []
    for cand in cand_paths:
        try:
            rel = cand.relative_to(super_root)
        except ValueError:
            continue
        if len(rel.parts) <= max_depth:
            out.append(cand)
    return sorted(set(out))

#TODO: this is very weak form of discovery, needs to be more robust
def classify_template(p: Path) -> str | None:
    """Return a template name understood by the single-dataset CLI, or None."""
    if (p / "dataset_description.json").exists():
        return "bids"
    if (p / "group_T1w.html").exists() or (p / "group_bold.html").exists():
        return "mriqc"
    if any((p / s / "stats" / "aseg.stats").exists() for s in p.glob("sub-*")):
        return "freesurfer"
    return None

@dataclass
class BuildResult:
    ds: Path
    kind: str
    ok: bool
    msg: str

def run_single(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def build_one(
    ds: Path,
    kind: str,
    single_cmd: str,
    out_root: Path,
    extra: List[str],
    dry: bool,
    in_flag: Optional[str],
    out_flag: str,
) -> BuildResult:
    out_dir = out_root / ds.name
    out_dir.mkdir(parents=True, exist_ok=True)

    if in_flag is None:
        cmd = [single_cmd, str(ds), out_flag, str(out_dir), "--template", kind, *extra]
    else:
        cmd = [single_cmd, in_flag, str(ds), out_flag, str(out_dir), "--template", kind, *extra]

    if dry:
        return BuildResult(ds, kind, True, f"DRY-RUN: {' '.join(cmd)}")

    proc = run_single(cmd)
    if proc.returncode != 0:
        return BuildResult(ds, kind, False, f"FAILED {ds} [{kind}]: {proc.stderr.strip() or proc.stdout.strip()}")
    return BuildResult(ds, kind, True, f"OK {ds} [{kind}]: {' '.join(cmd)}")

def write_book(book_dir: Path, ds_out_dirs: List[Path], template_dir: Optional[Path] = None) -> None:
    book_dir.mkdir(parents=True, exist_ok=True)

    # prepare context
    chapters = []
    for d in sorted(ds_out_dirs):
        nb = next(d.glob("*.ipynb"), None)
        md = next(d.glob("*.md"), None)
        if nb:
            target = nb
        elif md:
            target = md
        else:
            stub = (book_dir / f"{d.name}.md")
            stub.write_text(f"# {d.name}\n\n_Notebooks emitted to_: `{d}`\n")
            target = stub
        rel = target.relative_to(book_dir)
        chapters.append({
            "label": d.name.replace("_", " ").title(),
            "href": rel.with_suffix(".html").as_posix(),
            "toc_file": rel.with_suffix("").as_posix(),
        })

    context = {
        "title": "Flux Notebooks",
        "intro": "Per-dataset notebooks generated below.",
        "chapters": chapters,
        "execute_mode": "auto",
        "timeout": 120,
    }

    # load templates (default fallback if not provided)
    env = Environment(loader=FileSystemLoader(str(template_dir or book_dir.parent / "book_templates")))
    for tpl_name in ["index.md.j2", "_config.yml.j2", "_toc.yml.j2"]:
        tpl = env.get_template(tpl_name)
        out_name = tpl_name.replace(".j2", "")
        (book_dir / out_name).write_text(tpl.render(**context))


@app.command()
def main(
    super_path: Path = typer.Option(..., "--super", help="Path to superdataset root"),
    book: Path = typer.Option(..., "--book", help="Directory where the Jupyter Book scaffold goes"),
    book_templates: Optional[Path] = typer.Option(None, "--book-templates", help="Directory with Jinja2 templates for book"),
    out: Optional[Path] = typer.Option(None, "--out", help="Root dir for generated notebooks (default: <book>/notebooks)"),
    max_depth: int = typer.Option(3, help="Max depth for subdataset discovery"),
    workers: int = typer.Option(4, help="Parallel workers"),
    single_cmd: str = typer.Option("flux-notebooks", help="Single-dataset CLI to call"),
    extra: List[str] = typer.Option([], "--extra", help="Extra args forwarded to the single-dataset CLI"),
    dry_run: bool = typer.Option(False, help="Discover & print plan only"),
    force_clean: bool = typer.Option(False, help="Delete output/book dirs first"),
    in_flag: Optional[str] = typer.Option("--dataset", "--in-flag", help="Input flag for dataset path"),
    out_flag: str = typer.Option("--outdir", "--out-flag", help="Output flag"),
):
    super_path = super_path.resolve()
    book = book.resolve()
    out_root = (out or (book / "notebooks")).resolve()

    if force_clean:
        for p in (book, out_root):
            if p.exists():
                shutil.rmtree(p)

    # 1) discover all registered datasets, then classify
    candidates = discover_all_datasets(super_path, max_depth=max_depth)
    pairs: List[Tuple[Path, str]] = []
    for c in candidates:
        kind = classify_template(c)
        if kind:
            pairs.append((c, kind))

    if not pairs:
        typer.secho("No supported datasets found (looked for: bids, mriqc, freesurfer).", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    # Report what we found
    counts = {}
    for _, k in pairs:
        counts[k] = counts.get(k, 0) + 1
    found_msg = "Discovered datasets: " + ", ".join(f"{k}={counts[k]}" for k in sorted(counts))
    typer.secho(found_msg, fg=typer.colors.GREEN)

    # 2) build per dataset
    results: List[BuildResult] = []
    if dry_run:
        for ds, kind in pairs:
            results.append(build_one(ds, kind, single_cmd, out_root, extra, True, in_flag, out_flag))
    else:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futs = {
                pool.submit(build_one, ds, kind, single_cmd, out_root, extra, False, in_flag, out_flag): (ds, kind)
                for ds, kind in pairs
            }
            for f in as_completed(futs):
                results.append(f.result())

    ok = sum(r.ok for r in results)
    fail = len(results) - ok
    for r in results:
        typer.secho(r.msg, fg=(typer.colors.GREEN if r.ok else typer.colors.RED))
    typer.secho(f"\nSummary: {ok} OK, {fail} failed.", fg=typer.colors.BLUE)

    # 3) write the book scaffold
    if not dry_run:
        ds_out_dirs = [out_root / ds.name for ds, _ in pairs if (out_root / ds.name).exists()]
        #write_book(book, ds_out_dirs)
        write_book(book, ds_out_dirs, template_dir=book_templates)
        typer.secho(f"Book scaffold written to: {book}", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()
