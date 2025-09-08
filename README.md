# flux-notebooks

Generate reproducible Jupyter notebooks from datasets/projects available in GitLab and installable/searchable with [DataLad](https://www.datalad.org/).  


---

## Features

- **Notebook generation**: Create summary notebooks for BIDS datasets and their derivatives (e.g., FreeSurfer, MRIQC).
- **Superdataset support**: Walk an entire dataset hierarchy with DataLad and generate per-subdataset notebooks.
- **Jupyter Book integration**: Assemble all generated notebooks into a browsable, reproducible scientific report.
- **Extensible sections**: Modular “sections” system lets you add or reuse notebook components across pipelines (explorer, KPIs, QC, etc.).

There are two ways to run this code:

```flux-notebooks``` (single dataset mode):

- Generates a notebook and companion CSVs for one dataset.
- Useful if you only want to run on a single BIDS folder, or you’re testing/debugging a pipeline template.
- Output looks like your example (reports/bids_summary.ipynb, avail.csv, etc.).

```flux-notebooks-super``` (superdataset mode):

- Walks a DataLad superdataset and calls flux-notebooks under the hood for each subdataset (BIDS, freesurfer, mriqc, …).
- Collects all outputs into a Jupyter Book scaffold.
- Preferred workflow if you have multiple subdatasets.

## Quickstart

### Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

### Generate a single dataset notebook

```bash
flux-notebooks --dataset /path/to/BIDS --outdir ./reports --template bids
```

This will produce:

```bash
reports/
├── bids_summary.ipynb
├── avail.csv          # subject × datatype counts
├── func_counts.csv    # subject × task counts
└── tr_by_task.csv     # TR values by task
```

### Generate a superdataset jupyterbook 

This builds separate notebooks for each subdataset found inside a Datalad superdataset.

#### Example: Superdataset workflow

We provide a fake but reproducible superdataset under superdemo/ that mimics a realistic BIDS hierarchy with MRIQC and FreeSurfer derivatives. In real usage, you would just point to your own DataLad superdataset.

1. Create the demo superdataset:

```bash
python examples/generate_super_dataset.py ./superdemo
```
This creates a DataLad superdataset with BIDS, FreeSurfer, and MRIQC subdatasets.

2. Build notebooks + Jupyter Book

```bash
flux-notebooks-super --super ./superdemo --book ./book
jupyter-book build ./book
```

Then run:

```bash
python -m http.server -d book/_build/html 8001
```

to view the notebook in your browser. 


### Development & Contribution

- Templates:

    - Book templates live in ```book_templates/ (index.md.j2, _toc.yml.j2, _config.yml.j2)```.
    - Notebook templates live in ```src/flux_notebooks/notebooks/templates/```.

- Sections:

    - Shared notebook sections are defined in ```src/flux_notebooks/notebooks/sections.py```.
    - Add a new section here to make it available across pipelines (BIDS, FreeSurfer, MRIQC, …).

- Pipelines:

    - Each dataset type (bids, freesurfer, mriqc) has a builder.py in ```src/flux_notebooks/notebooks/{pipeline}/```.
    - Builders call into sections to assemble notebooks.

- Example data:
    - superdemo/ is a Git-annex-backed fake dataset for testing.
    - Always regenerate it via examples/generate_super_dataset.py rather than committing raw files.

### Roadmap

- Expand supported pipelines/subdataserts 
- Improve visualization defaults.
- Enable live cells (can be run by users)
- Add tests around flux-notebooks-super orchestration.
    
