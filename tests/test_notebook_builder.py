from pathlib import Path

import nbformat as nbf

from flux_notebooks.notebooks.builder import render_notebook


def test_template_renders(tmp_path: Path):
    tpldir = Path("src/flux_notebooks/notebooks/templates")
    nb = render_notebook(
        template_dir=tpldir,
        template_name="summary.ipynb.j2",
        context={
            "dataset_root": "/tmp/ds",
            "generated": "2025-01-01 00:00 UTC",
            "n_subjects": 0,
            "n_sessions": 0,
            "n_tasks": 0,
            "datatypes": [],
            "outdir": str(tmp_path),
        },
    )
    assert isinstance(nb, nbf.NotebookNode)
