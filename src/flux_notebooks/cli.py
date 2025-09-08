# src/flux_notebooks/cli.py
from __future__ import annotations
from pathlib import Path
import datetime as _dt
import importlib
import typer

from .config import Settings

app = typer.Typer(add_completion=False)

def _load_template(name: str):
    try:
        return importlib.import_module(f".notebooks.templates.{name}.builder", package="flux_notebooks")
    except ModuleNotFoundError as e:
        raise typer.BadParameter(f"Unknown --template '{name}'. Available: bids, mriqc, freesurfer") from e

@app.command()
def generate(
    dataset: str = typer.Option(..., "--dataset", help="Path to dataset root"),
    outdir: str = typer.Option("./reports", "--outdir", help="Output directory"),
    template: str = typer.Option("bids", "--template", case_sensitive=False, help="bids | mriqc | freesurfer"),
    validate: bool = typer.Option(False, "--validate", help="BIDS validation (bids template only)"),
):
    """
    Generate a summary notebook using the selected template.
    """
    settings = Settings(
        dataset_root=Path(dataset).resolve(),
        outdir=Path(outdir).resolve(),
        validate_bids=validate,
    )
    settings.outdir.mkdir(parents=True, exist_ok=True)
    generated = _dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    tpl = _load_template(template.lower())
    # Every template exposes: summarize(settings, generated) -> context, build(context) -> nb, output_name
    context = tpl.summarize(settings, generated)
    nb = tpl.build(context)
    out_nb = settings.outdir / tpl.output_name
    from .notebooks.builder import write_notebook  
    write_notebook(nb, out_nb)
    typer.echo(f"Wrote: {out_nb}")

if __name__ == "__main__":
    app()
