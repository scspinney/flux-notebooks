# src/flux_notebooks/cli/report.py
from __future__ import annotations
import argparse, os
from pathlib import Path
from datetime import datetime

def main(argv=None):
    ap = argparse.ArgumentParser(description="Execute a report template (py/ipynb) with papermill")
    ap.add_argument("--template", required=True, help="Template .py or .ipynb")
    ap.add_argument("--output",   required=True, help="Output notebook .ipynb")
    ap.add_argument("--outdir",   required=True, help="Directory where the template writes CSVs, etc.")
    ap.add_argument("--dataset-root", default=os.environ.get("FLUX_DATASET_ROOT"),
                    help="Dataset root (or set FLUX_DATASET_ROOT)")
    args = ap.parse_args(argv)

    template = Path(args.template).resolve()
    output   = Path(args.output).resolve()
    outdir   = Path(args.outdir).resolve()
    dataset_root = Path(args.dataset_root).resolve() if args.dataset_root else None

    output.parent.mkdir(parents=True, exist_ok=True)
    outdir.mkdir(parents=True, exist_ok=True)

    params = {
        "dataset_root": str(dataset_root) if dataset_root else "",
        "outdir": str(outdir),
        "generated": datetime.now().isoformat(timespec="seconds"),
    }

    import papermill as pm
    pm.execute_notebook(
        input_path=str(template),
        output_path=str(output),
        parameters=params,
        cwd=str(template.parent),
        engine_name="python",
    )

if __name__ == "__main__":
    main()
