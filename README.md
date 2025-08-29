# flux-notebooks

Generate reproducible Jupyter notebooks from datasets/projects available in GitLab and searchable/installable with DataLad. BIDS-aware via PyBIDS.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
flux-notebooks generate --dataset /path/to/BIDS --outdir ./reports
```

Outputs:

    - reports/bids_summary.ipynb
    - reports/avail.csv (subject × datatype counts)
    - reports/func_counts.csv (subject × task counts for func)

