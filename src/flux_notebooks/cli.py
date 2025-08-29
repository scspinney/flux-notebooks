from __future__ import annotations

from pathlib import Path
import datetime as _dt

import typer

from .bids.summarize_bids import summarize_with_pybids
from .config import Settings
from .notebooks.builder import build_summary_notebook, save_tables, write_notebook

app = typer.Typer(add_completion=False)


@app.command()
def generate(
    dataset: str = typer.Option(..., "--dataset", help="Path to dataset root (BIDS)"),
    outdir: str = typer.Option("./reports", "--outdir", help="Output directory"),
    validate: bool = typer.Option(False, "--validate", help="PyBIDS layout validation"),
):
    """
    Generate a summary notebook for a BIDS dataset (PyBIDS-powered).
    """
    settings = Settings(
        dataset_root=Path(dataset).resolve(),
        outdir=Path(outdir).resolve(),
        validate_bids=validate,
    )
    settings.outdir.mkdir(parents=True, exist_ok=True)

    summary = summarize_with_pybids(settings.dataset_root, validate=settings.validate_bids)
    save_tables(summary, settings.outdir)

    context = {
        "dataset_root": settings.dataset_root,
        "outdir": settings.outdir,
        "generated": _dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "n_subjects": len(summary["subjects"]),
        "n_sessions": len(summary["sessions"]),
        "n_tasks": len(summary["tasks"]),
        "datatypes": summary["datatypes"],
    }
    nb = build_summary_notebook(context)
    out_nb = settings.outdir / "bids_summary.ipynb"
    write_notebook(nb, out_nb)
    typer.echo(f"Wrote: {out_nb}")


if __name__ == "__main__":
    app()
