# src/flux_notebooks/lib/common.py
from __future__ import annotations

from pathlib import Path
import os
import re
from typing import List, Dict, Any

import pandas as pd
from IPython.display import display, Markdown, clear_output, HTML

# Try to import widgets, but don't crash the build if missing
try:
    import ipywidgets as widgets
    from ipywidgets import Layout, GridBox

    _HAVE_WIDGETS = True
except Exception:
    widgets = None  # type: ignore[assignment]
    Layout = GridBox = None  # type: ignore[assignment]
    _HAVE_WIDGETS = False

def bids_dashboard(summary):
    panels = []

    if "avail" in summary:
        out = widgets.Output()
        with out:
            display(summary["avail"])
        panels.append(
            widgets.VBox([
                widgets.HTML("<b>Availability by datatype</b>"),
                out
            ])
        )

    if "func_counts" in summary:
        out = widgets.Output()
        with out:
            display(summary["func_counts"])
        panels.append(
            widgets.VBox([
                widgets.HTML("<b>Functional runs per task</b>"),
                out
            ])
        )

    if "tr_by_task" in summary:
        out = widgets.Output()
        with out:
            display(summary["tr_by_task"])
        panels.append(
            widgets.VBox([
                widgets.HTML("<b>TR summary by task</b>"),
                out
            ])
        )

    return widgets.VBox(panels)


# ---------------------------------------------------------------------
# Save common summary tables (CSV) — used by BIDS & friends
# ---------------------------------------------------------------------
def save_summary_tables(summary: Dict[str, Any], outdir: Path) -> List[Path]:
    """
    Save any pandas.DataFrame values in `summary` to CSV files in `outdir`.
    Files are named with a 'bids_' prefix plus the dict key (e.g., bids_avail.csv).
    Returns the list of saved paths.
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []
    for key, val in summary.items():
        if isinstance(val, pd.DataFrame) and not val.empty:
            path = outdir / f"bids_{key}.csv"
            # Write index only when it carries meaning (e.g., pivoted tables). Default False.
            index_flag = key in {"func_counts"}
            val.to_csv(path, index=index_flag)
            saved.append(path)
    return saved


# ---------------------------------------------------------------------
# BIDS explorer (widget-based; importable and testable — no code strings)
# ---------------------------------------------------------------------
def _maybe_bids_layout(base: Path):
    try:
        from bids import BIDSLayout

        return BIDSLayout(base, validate=False)
    except Exception as e:
        # Non-fatal: we can fall back to string search
        display(Markdown(f"_PyBIDS init failed (fallback to string search): {e}_"))
        return None


def _options(layout):
    if layout is None:
        return [], [], [], [], []

    def safe(getter, *args, **kw):
        try:
            return sorted(getter(*args, **kw))
        except Exception:
            return []

    return (
        safe(layout.get_subjects),
        safe(layout.get_sessions),
        safe(layout.get_tasks),
        safe(layout.get, return_type="id", target="datatype"),
        safe(layout.get, return_type="id", target="suffix"),
    )


def _search_paths(base: Path, layout, ents: dict) -> list[str]:
    if layout is not None:
        try:
            return layout.get(return_type="file", **ents)
        except Exception:
            pass
    # Fallback: brute-force walk (ignores ents)
    paths: list[str] = []
    for p, _, fs in os.walk(base):
        for f in fs:
            paths.append(os.path.join(p, f))
    return paths


def _filter_and_tabulate(
    paths: list[str],
    base: Path,
    layout,
    cols: list[str],
    contains: str,
    limit: int,
) -> pd.DataFrame:
    if contains:
        tokens = [t.lower() for t in re.split(r"\s+", contains) if t]

        def ok(s: str) -> bool:
            s = s.lower()
            return all(t in s for t in tokens)

        paths = [p for p in paths if ok(p)]
    paths = sorted(set(paths))[: int(limit)]
    rows = []
    for p in paths:
        rel = os.path.relpath(p, base)
        row = {"path": rel}
        if layout is not None:
            try:
                e = layout.parse_file_entities(p)
                for k in ("subject", "session", "task", "run", "datatype", "suffix"):
                    if k in e:
                        row[k] = e[k]
            except Exception:
                pass
        rows.append(row)
    df = pd.DataFrame(rows)
    ordered = ["path"] + [c for c in cols if c in df.columns]
    return df[ordered + [c for c in df.columns if c not in ordered]]


def bids_explorer(dataset_root: Path):
    """
    Return a VBox widget containing the BIDS explorer UI.
    If ipywidgets is unavailable, display a one-shot static table instead and return None.
    """
    base = Path(dataset_root)
    layout = _maybe_bids_layout(base)
    sub_opts, ses_opts, task_opts, dt_opts, suf_opts = _options(layout)

    # Fallback if widgets are not available: show a static snapshot and bail.
    if not _HAVE_WIDGETS:
        paths = _search_paths(base, layout, ents={})
        df = _filter_and_tabulate(
            paths, base, layout, ["subject", "task", "datatype", "suffix"], "", 200
        )
        if df.empty:
            display(
                Markdown(
                    "_BIDS Explorer unavailable (ipywidgets not installed) and no files found._"
                )
            )
            return None
        display(
            Markdown(
                "**BIDS Explorer unavailable (ipywidgets not installed). Showing a static snapshot:**"
            )
        )
        html = df.to_html(index=False, escape=False, max_rows=None, max_cols=None)
        display(
            HTML(
                "<div style='max-height:520px; overflow:auto; width:100%; border:1px solid #ddd; "
                "border-radius:6px; padding:6px;'>" + html + "</div>"
            )
        )
        return None

    # --- Interactive UI (widgets available) ---
    W_SELECT = "260px"
    W_SHORT = "260px"
    DESC_W = "80px"
    TABLE_HEIGHT = "520px"

    def _select_multi(description, options, rows):
        w = widgets.SelectMultiple(
            options=options,
            rows=min(rows, max(3, len(options))) if options else 3,
            description=description,
            layout=Layout(width=W_SELECT),
            style={"description_width": DESC_W},
        )
        all_btn = widgets.Button(description="All", layout=Layout(width="70px"))
        none_btn = widgets.Button(description="None", layout=Layout(width="70px"))
        all_btn.on_click(lambda _: setattr(w, "value", tuple(w.options)))
        none_btn.on_click(lambda _: setattr(w, "value", ()))
        return w, widgets.HBox([all_btn, none_btn], layout=Layout(gap="6px"))

    sub_w, sub_btns = _select_multi("subject", sub_opts, 10)
    ses_w, ses_btns = _select_multi("session", ses_opts, 6)
    task_w, task_btns = _select_multi("task", task_opts, 6)
    dt_w, dt_btns = _select_multi("datatype", dt_opts, 6)
    suf_w, suf_btns = _select_multi("suffix", suf_opts, 6)

    txt_w = widgets.Text(
        value="",
        description="contains",
        placeholder="e.g. T1w.json",
        layout=Layout(width=W_SHORT),
        style={"description_width": DESC_W},
        continuous_update=False,
    )
    limit_w = widgets.IntSlider(
        value=200,
        min=50,
        max=2000,
        step=50,
        description="limit",
        layout=Layout(width=W_SHORT),
        style={"description_width": DESC_W},
        continuous_update=False,
    )
    cols_w = widgets.SelectMultiple(
        options=["subject", "session", "task", "run", "datatype", "suffix"],
        value=("subject", "task", "datatype", "suffix"),
        description="cols",
        layout=Layout(width=W_SHORT),
        style={"description_width": DESC_W},
    )

    search_btn = widgets.Button(
        description="Search", button_style="primary", layout=Layout(width="140px")
    )
    clear_btn = widgets.Button(
        description="Clear all", button_style="warning", layout=Layout(width="140px")
    )
    out_area = widgets.Output()

    def run_search(_=None):
        with out_area:
            clear_output(wait=True)
            ents = {}
            if sub_w.value:
                ents["subject"] = list(sub_w.value)
            if ses_w.value:
                ents["session"] = list(ses_w.value)
            if task_w.value:
                ents["task"] = list(task_w.value)
            if dt_w.value:
                ents["datatype"] = list(dt_w.value)
            if suf_w.value:
                ents["suffix"] = list(suf_w.value)
            paths = _search_paths(base, layout, ents)
            df = _filter_and_tabulate(
                paths, base, layout, list(cols_w.value), txt_w.value, int(limit_w.value)
            )
            if df.empty:
                display(Markdown("_No matches._"))
                return
            html = df.to_html(index=False, escape=False, max_rows=None, max_cols=None)
            display(
                HTML(
                    "<div style='max-height:%s; overflow:auto; width:100%%; border:1px solid #ddd; "
                    "border-radius:6px; padding:6px;'>%s</div>" % (TABLE_HEIGHT, html)
                )
            )

    def clear_all(_):
        sub_w.value = ()
        ses_w.value = ()
        task_w.value = ()
        dt_w.value = ()
        suf_w.value = ()
        txt_w.value = ""
        run_search()

    search_btn.on_click(run_search)
    clear_btn.on_click(clear_all)
    txt_w.observe(
        lambda ch: run_search() if ch["name"] == "value" and ch["type"] == "change" else None,
        names="value",
    )

    grid = GridBox(
        children=[
            sub_w,
            ses_w,
            task_w,
            sub_btns,
            ses_btns,
            task_btns,
            dt_w,
            suf_w,
            widgets.VBox(
                [widgets.HBox([txt_w, limit_w], layout=Layout(gap="12px")), cols_w]
            ),
            dt_btns,
            suf_btns,
            widgets.HBox([search_btn, clear_btn], layout=Layout(gap="12px")),
        ],
        layout=Layout(
            grid_template_columns="repeat(3, 260px)",
            grid_gap="10px 20px",
            align_items="flex-start",
            width="100%",
        ),
    )

    out_area.clear_output(wait=True)
    run_search()
    return widgets.VBox([grid, out_area])


def display_bids_explorer(dataset_root: Path) -> None:
    """Convenience wrapper that immediately displays the explorer."""
    display(bids_explorer(dataset_root))


# Back-compat alias used by older notebooks
def show_bids_explorer(dataset_root: Path) -> None:
    display_bids_explorer(dataset_root)


__all__ = [
    "bids_explorer",
    "display_bids_explorer",
    "show_bids_explorer",
    "save_summary_tables",
    # The following are useful for unit tests
    "_filter_and_tabulate",
    "_search_paths",
    "_maybe_bids_layout",
    "_options",
]



def is_preprocessed(sub_id: str, derivatives_root: Path) -> bool:
    """
    Check if the subject has final pipeline outputs (MRIQC, fMRIPrep, or FreeSurfer).
    """
    sub_id = sub_id.replace("sub-", "")
    processed = False

    # MRIQC
    mriqc_path = derivatives_root / "mriqc" / f"sub-{sub_id}"
    if any(mriqc_path.glob("**/*.html")) or any(mriqc_path.glob("**/*.json")):
        processed = True

    # fMRIPrep
    fmriprep_path = derivatives_root / "fmriprep" / f"sub-{sub_id}"
    if any(fmriprep_path.glob("**/*.html")) or any(fmriprep_path.glob("**/*confounds_timeseries.tsv")):
        processed = True

    # FreeSurfer
    fs_path = derivatives_root / "freesurfer" / f"sub-{sub_id}"
    if (fs_path / "stats").exists() and (fs_path / "surf").exists():
        processed = True

    return processed
