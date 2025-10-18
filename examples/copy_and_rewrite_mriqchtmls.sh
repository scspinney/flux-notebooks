#!/usr/bin/env bash
# -------------------------------------------------------------
# Copy example MRIQC HTMLs to each subject's folder, renaming
# and rewriting internal figure paths.
#
# Usage:
#   ./copy_and_rewrite_mriqc_htmls.sh [EXAMPLE_DIR] [DEST_DIR] [N_SUBS] [N_SES]
#
# Defaults:
#   EXAMPLE_DIR = /home/ubuntu/local_gitlab/flux-notebooks/data/mriqc_reports_example
#   DEST_DIR    = /home/ubuntu/local_gitlab/flux-notebooks/superdemo_real/qc/mriqc
#   N_SUBS      = 3
#   N_SES       = 2
# -------------------------------------------------------------

set -euo pipefail

# --- Default parameters ---
EXAMPLE_DIR=${1:-/home/ubuntu/local_gitlab/flux-notebooks/data/mriqc_reports_example}
DEST_DIR=${2:-/home/ubuntu/local_gitlab/flux-notebooks/superdemo_real/qc/mriqc}
N_SUBS=${3:-3}
N_SES=${4:-2}

# --- Verify input ---
if [[ ! -d "$EXAMPLE_DIR" ]]; then
  echo "❌ Example directory not found: $EXAMPLE_DIR"
  exit 1
fi

mkdir -p "$DEST_DIR"

# --- Detect subject/session tokens ---
SAMPLE_HTML=$(find "$EXAMPLE_DIR" -maxdepth 1 -type f -name "*.html" | head -n 1)
[[ -z "$SAMPLE_HTML" ]] && { echo "❌ No HTML files found in $EXAMPLE_DIR"; exit 1; }

EXAMPLE_SUB=$(grep -oE 'sub-[0-9]+' <<< "$SAMPLE_HTML" | head -n 1 || echo "sub-001")
EXAMPLE_SES=$(grep -oE 'ses-[0-9a-z]+' <<< "$SAMPLE_HTML" | head -n 1 || echo "ses-2a")

echo "📂 Using example data from: $EXAMPLE_DIR"
echo "🔍 Detected tokens: $EXAMPLE_SUB / $EXAMPLE_SES"
echo "🧩 Generating $N_SUBS subjects × $N_SES sessions..."
echo

# --- Main loop ---
for ((i=1; i<=N_SUBS; i++)); do
  sub_id=$(printf "sub-%03d" "$i")
  sub_dir="${DEST_DIR}/${sub_id}"
  mkdir -p "$sub_dir"

  for ((j=1; j<=N_SES; j++)); do
    ses_id="ses-${j}a"
    ses_dir="${sub_dir}/${ses_id}"
    mkdir -p "$ses_dir"

    for html in "$EXAMPLE_DIR"/*.html; do
      base=$(basename "$html")
      new_base="${base//$EXAMPLE_SUB/$sub_id}"
      new_base="${new_base//$EXAMPLE_SES/$ses_id}"
      dest_file="${ses_dir}/${new_base}"

      sed -e "s|${EXAMPLE_SUB}|${sub_id}|g" \
          -e "s|${EXAMPLE_SES}|${ses_id}|g" \
          -e "s|figures/|../../${sub_id}/figures/|g" \
          "$html" > "$dest_file"

      echo "→ Created: $dest_file"
    done
  done
done

echo
echo "✅ Done."
echo "Check with:"
echo "  find \"$DEST_DIR\" -name '*.html' | wc -l"
echo "  and open one in your browser to confirm figures display correctly."
