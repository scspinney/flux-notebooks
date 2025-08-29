#!/usr/bin/env bash
set -euo pipefail
dataset="${1:-/path/to/BIDS}"
outdir="${2:-./reports}"
flux-notebooks generate --dataset "$dataset" --outdir "$outdir"
echo "Notebook in $outdir/bids_summary.ipynb"
