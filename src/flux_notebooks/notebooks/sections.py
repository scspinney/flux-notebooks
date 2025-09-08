# src/flux_notebooks/notebooks/sections.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Iterable, List, Callable
import nbformat as nbf

# === primitives ===
def _md(text: str): return nbf.v4.new_markdown_cell(text)
def _code(src: str): return nbf.v4.new_code_cell(src)

Section = Callable[[Dict,], Iterable[nbf.NotebookNode]]
REGISTRY: Dict[str, Section] = {}

def register(name: str):
    def deco(fn: Section) -> Section:
        REGISTRY[name] = fn
        return fn
    return deco

def get_sections(names: List[str]) -> List[Section]:
    missing = [n for n in names if n not in REGISTRY]
    if missing:
        raise KeyError(f"Unknown section(s): {missing}")
    return [REGISTRY[n] for n in names]

# =========================
# BIDS sections (existing)
# =========================

@register("bids:intro")
def intro_section(ctx: Dict) -> Iterable[nbf.NotebookNode]:
    dataset_root: Path = ctx["dataset_root"]
    generated: str = ctx["generated"]
    yield _md(
        f"# BIDS Summary \n"
        f"**Root:** `{dataset_root}`  \n"
        f"**Generated:** {generated}\n"
    )

@register("bids:init")
def init_section(ctx: Dict) -> Iterable[nbf.NotebookNode]:
    outdir: Path = ctx["outdir"]
    n_subjects: int = ctx["n_subjects"]
    n_sessions: int = ctx["n_sessions"]
    n_tasks: int = ctx["n_tasks"]
    datatypes: List[str] = ctx["datatypes"]

    css = """# See notebook CSS stub; currently disabled."""
    yield _code(css)

    src = f"""from pathlib import Path
import json, os, re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import ipywidgets as widgets
from IPython.display import display, Markdown

outdir = Path(r'{outdir}')
avail = pd.read_csv(outdir/'avail.csv') if (outdir/'avail.csv').exists() else None
func  = pd.read_csv(outdir/'func_counts.csv') if (outdir/'func_counts.csv').exists() else None

pd.set_option('display.max_colwidth', None)
plt.rcParams['figure.figsize'] = (10, 4)
plt.rcParams['figure.dpi'] = 120

n_subjects={n_subjects}; n_sessions={n_sessions}; n_tasks={n_tasks}; datatypes={datatypes}
print('Subjects:', n_subjects)
print('Sessions:', n_sessions)
print('Tasks:', n_tasks)
print('Datatypes:', datatypes)
"""
    yield _code(src)

@register("bids:metadata")
def metadata_section(ctx: Dict) -> Iterable[nbf.NotebookNode]:
    dataset_root: Path = ctx["dataset_root"]
    yield _md("## Dataset metadata\nWe try to read `dataset_description.json` and `participants.tsv` if present.")
    src = f"""from pathlib import Path
import json
import pandas as pd
from IPython.display import display, Markdown

ds_desc_path = Path(r'{dataset_root}')/'dataset_description.json'
ds_desc = json.loads(ds_desc_path.read_text()) if ds_desc_path.exists() else {{}}
display(pd.DataFrame([ds_desc])) if ds_desc else display(Markdown('_No dataset_description.json found._'))

pt_path = Path(r'{dataset_root}')/'participants.tsv'
participants = pd.read_csv(pt_path, sep='\\t', dtype=str) if pt_path.exists() else None
if isinstance(participants, pd.DataFrame):
    display(participants.head())
    if any(c.lower().startswith('age') for c in participants.columns):
        age_col = [c for c in participants.columns if c.lower().startswith('age')][0]
        with pd.option_context('mode.use_inf_as_na', True):
            ages = pd.to_numeric(participants[age_col], errors='coerce')
        display(pd.DataFrame({{'n': [ages.notna().sum()], 'min':[ages.min()], 'median':[ages.median()], 'max':[ages.max()]}}))
    if any(c.lower() in ('sex','gender') for c in participants.columns):
        sex_col = [c for c in participants.columns if c.lower() in ('sex','gender')][0]
        display(participants[sex_col].str.lower().value_counts().rename_axis('sex').to_frame('count'))
else:
    display(Markdown('_No participants.tsv found._'))
"""
    yield _code(src)

@register("bids:kpi")
def kpi_section(ctx: Dict) -> Iterable[nbf.NotebookNode]:
    dataset_root: Path = ctx["dataset_root"]
    yield _md("## KPIs")
    src = f"""from collections import defaultdict
import os, pandas as pd
from pathlib import Path
size_by_dt = defaultdict(int)
try:
    # Use avail to decide which top-level datatypes to scan
    if isinstance(avail, pd.DataFrame):
        for dt in avail.columns:
            dt_dir = Path(r'{dataset_root}')/dt
            if dt_dir.exists():
                for p,_,files in os.walk(dt_dir):
                    for f in files:
                        try:
                            size_by_dt[dt] += (Path(p)/f).stat().st_size
                        except Exception:
                            pass
    size_df = pd.DataFrame({{'datatype': list(size_by_dt.keys()), 'GB': [v/(1024**3) for v in size_by_dt.values()]}})
    if not size_df.empty:
        display(size_df.sort_values('GB', ascending=False).reset_index(drop=True))
except Exception as e:
    print('Size calc skipped:', e)
"""
    yield _code(src)

@register("bids:availability")
def availability_section(ctx: Dict) -> Iterable[nbf.NotebookNode]:
    yield _md("## Subject × datatype availability")
    src = """import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

if isinstance(avail, pd.DataFrame):
    A = avail.copy()
    if 'sub' in A.columns:
        A = A.set_index('sub')
    display(A)

    totals = A.sum(axis=0).sort_values(ascending=False)
    plt.figure(figsize=(max(8, 0.6*len(totals)), 4))
    totals.plot(kind='bar')
    plt.ylabel('files'); plt.title('Total files per datatype')
    plt.tight_layout(); plt.show()

    per_sub = A.sum(axis=1).sort_values(ascending=False)
    plt.figure(figsize=(max(8, 0.35*len(per_sub)), 4))
    per_sub.plot(kind='bar')
    plt.ylabel('files'); plt.title('Total files per subject')
    plt.tight_layout(); plt.show()
else:
    display('No availability table.')
"""
    yield _code(src)

@register("bids:func_runs")
def func_runs_section(ctx: Dict) -> Iterable[nbf.NotebookNode]:
    yield _md("## Functional runs by task (interactive)")
    src = """import matplotlib.pyplot as plt
import ipywidgets as widgets
from IPython.display import display

if isinstance(func, pd.DataFrame) and not func.empty:
    func = func.set_index('subject') if 'subject' in func.columns else func
    tasks = list(func.columns)
    task_dd = widgets.Dropdown(options=tasks, description='Task')

    def _bar(task):
        s = func[task].sort_values(ascending=False)
        plt.figure(figsize=(max(10, 0.35*len(s)), 4))
        s.plot(kind='bar')
        plt.ylabel('# runs'); plt.title(f'Runs per subject — {task}')
        plt.tight_layout(); plt.show()

    out = widgets.interactive_output(_bar, {'task': task_dd})
    display(task_dd, out)
else:
    display('No functional runs found.')
"""
    yield _code(src)

@register("bids:tr")
def tr_section(ctx: Dict) -> Iterable[nbf.NotebookNode]:
    yield _md("## Functional TR by task")
    src = """import pandas as pd
from IPython.display import display

tr_csv = outdir/'tr_by_task.csv'
tr_by_task = pd.read_csv(tr_csv) if tr_csv.exists() else None
display(tr_by_task if isinstance(tr_by_task, pd.DataFrame) else 'TR table not available in this build.')
"""
    yield _code(src)

@register("common:explorer")
def explorer_section(ctx: Dict) -> Iterable[nbf.NotebookNode]:
    dataset_root: Path = ctx["dataset_root"]
    code = f"""from pathlib import Path
import os, re
import pandas as pd
import ipywidgets as widgets
from ipywidgets import Layout, GridBox
from IPython.display import display, Markdown, clear_output, HTML

pd.set_option('display.max_colwidth', None)

try:
    from bids import BIDSLayout
    layout = BIDSLayout(Path(r'{dataset_root}'), validate=False)
except Exception as e:
    layout = None
    display(Markdown(f"_PyBIDS init failed (fallback to string search): {{str(e)}}_"))

base = Path(r'{dataset_root}')
sub_opts  = sorted(layout.get_subjects()) if layout else []
ses_opts  = sorted(layout.get_sessions()) if layout else []
task_opts = sorted(layout.get_tasks()) if layout else []
dt_opts   = sorted(layout.get(return_type='id', target='datatype')) if layout else []
suf_opts  = sorted(layout.get(return_type='id', target='suffix')) if layout else []

W_SELECT='260px'; W_SHORT='260px'; DESC_W='80px'; TABLE_HEIGHT='520px'

def _select_multi(description, options, rows):
    w = widgets.SelectMultiple(options=options, rows=min(rows, max(3, len(options))) if options else 3,
                               description=description, layout=Layout(width=W_SELECT), style={{'description_width': DESC_W}})
    all_btn  = widgets.Button(description='All',  layout=Layout(width='70px'))
    none_btn = widgets.Button(description='None', layout=Layout(width='70px'))
    def set_all(_):  w.value = tuple(w.options)
    def set_none(_): w.value = ()
    all_btn.on_click(set_all); none_btn.on_click(set_none)
    return w, widgets.HBox([all_btn, none_btn], layout=Layout(gap='6px'))

sub_w,  sub_btns  = _select_multi('subject',  sub_opts, 10)
ses_w,  ses_btns  = _select_multi('session',  ses_opts,  6)
task_w, task_btns = _select_multi('task',     task_opts, 6)
dt_w,   dt_btns   = _select_multi('datatype', dt_opts,   6)
suf_w,  suf_btns  = _select_multi('suffix',   suf_opts,  6)

txt_w = widgets.Text(value='', description='contains', placeholder='e.g. T1w.json',
                     layout=Layout(width=W_SHORT), style={{'description_width': DESC_W}}, continuous_update=False)
limit_w = widgets.IntSlider(value=200, min=50, max=2000, step=50, description='limit',
                            layout=Layout(width=W_SHORT), style={{'description_width': DESC_W}}, continuous_update=False)
cols_w  = widgets.SelectMultiple(options=['subject','session','task','run','datatype','suffix'],
                                 value=('subject','task','datatype','suffix'),
                                 description='cols', layout=Layout(width=W_SHORT), style={{'description_width': DESC_W}})

search_btn = widgets.Button(description='Search', button_style='primary', layout=Layout(width='140px'))
clear_btn  = widgets.Button(description='Clear all', button_style='warning', layout=Layout(width='140px'))
out_area   = widgets.Output()

def run_search(_=None):
    with out_area:
        clear_output(wait=True)
        ents = {{}}
        if sub_w.value:  ents['subject']  = list(sub_w.value)
        if ses_w.value:  ents['session']  = list(ses_w.value)
        if task_w.value: ents['task']     = list(task_w.value)
        if dt_w.value:   ents['datatype'] = list(dt_w.value)
        if suf_w.value:  ents['suffix']   = list(suf_w.value)

        try:
            if layout:
                paths = layout.get(return_type='file', **ents)
            else:
                paths = []
                for p,_,fs in os.walk(base):
                    for f in fs:
                        paths.append(os.path.join(p, f))
        except Exception as e:
            display(Markdown(f"_Query error: {{str(e)}}_")); return

        contains = txt_w.value.strip()
        if contains:
            import re
            tokens = [t.lower() for t in re.split(r"\\s+", contains) if t]
            def ok(s):
                s = s.lower()
                return all(t in s for t in tokens)
            paths = [p for p in paths if ok(p)]

        paths = sorted(set(paths))[: int(limit_w.value)]
        if not paths:
            display(Markdown('_No matches._')); return

        rows = []
        for p in paths:
            rel = os.path.relpath(p, base)
            row = {{'path': rel}}
            if layout:
                e = layout.parse_file_entities(p)
                for k in ('subject','session','task','run','datatype','suffix'):
                    if k in e: row[k] = e[k]
            rows.append(row)

        import pandas as pd
        df = pd.DataFrame(rows)
        ordered = ['path'] + [c for c in cols_w.value if c in df.columns]
        df = df[ordered + [c for c in df.columns if c not in ordered]]
        from IPython.display import HTML
        html = df.to_html(index=False, escape=False, max_rows=None, max_cols=None)
        display(HTML("<div style='max-height:520px; overflow:auto; width:100%; border:1px solid #ddd; border-radius:6px; padding:6px;'>" + html + "</div>"))

def clear_all(_):
    sub_w.value = (); ses_w.value = (); task_w.value = ()
    dt_w.value  = (); suf_w.value  = (); txt_w.value  = ''
    run_search()

search_btn.on_click(run_search)
clear_btn.on_click(clear_all)
txt_w.observe(lambda ch: run_search() if ch['name']=='value' and ch['type']=='change' else None, names='value')

from ipywidgets import GridBox, Layout
grid = GridBox(children=[
    sub_w,  ses_w,  task_w,
    sub_btns, ses_btns, task_btns,
    dt_w,    suf_w,  widgets.VBox([widgets.HBox([txt_w, limit_w], layout=Layout(gap='12px')), cols_w]),
    dt_btns, suf_btns, widgets.HBox([search_btn, clear_btn], layout=Layout(gap='12px')),
], layout=Layout(grid_template_columns='repeat(3, 260px)', grid_gap='10px 20px', align_items='flex-start', width='100%'))
display(grid, out_area)
run_search()
"""
    return [_md("## Explore files (BIDS explorer + substring search)"), _code(code)]

# =========================
# MRIQC sections
# =========================

@register("mriqc:header")
def mriqc_header(ctx: Dict) -> Iterable[nbf.NotebookNode]:
    root: Path = ctx["dataset_root"]; gen: str = ctx["generated"]
    yield _md(f"# MRIQC Summary\n**Root:** `{root}`  \n**Generated:** {gen}")

@register("mriqc:group_reports")
def mriqc_group_reports(ctx: Dict) -> Iterable[nbf.NotebookNode]:
    root: Path = ctx["dataset_root"]
    yield _md("## Group reports")
    yield _code(
        "from pathlib import Path\n"
        f"root = Path(r'''{root}''')\n"
        "sorted([p.name for p in root.glob('group_*.html')])"
    )

@register("mriqc:t1w_metrics")
def mriqc_t1w_metrics(ctx: Dict) -> Iterable[nbf.NotebookNode]:
    root: Path = ctx["dataset_root"]
    yield _md("## Subject metrics (T1w)")
    yield _code(
        "import json, pandas as pd\n"
        "from pathlib import Path\n"
        f"root = Path(r'''{root}''')\n"
        "rows = []\n"
        "for j in root.glob('sub-*_T1w.json'):\n"
        "    try:\n"
        "        d = json.loads(j.read_text())\n"
        "        rows.append({'subject': d.get('bids_name', j.stem.split('_')[0]), 'cjv': d.get('cjv')})\n"
        "    except Exception:\n"
        "        pass\n"
        "pd.DataFrame(rows).sort_values('subject')"
    )

# =========================
# FreeSurfer sections
# =========================

@register("fs:header")
def fs_header(ctx: Dict) -> Iterable[nbf.NotebookNode]:
    root: Path = ctx["dataset_root"]; gen: str = ctx["generated"]
    yield _md(f"# FreeSurfer Summary\n**Root:** `{root}`  \n**Generated:** {gen}")

@register("fs:subjects_table")
def fs_subjects_table(ctx: Dict) -> Iterable[nbf.NotebookNode]:
    root: Path = ctx["dataset_root"]
    yield _md("## Subjects & stats availability")
    yield _code(
        "from pathlib import Path\n"
        "import pandas as pd\n"
        f"root = Path(r'''{root}''')\n"
        "rows = []\n"
        "for subj in sorted([p for p in root.glob('sub-*') if p.is_dir()]):\n"
        "    aseg = subj / 'stats' / 'aseg.stats'\n"
        "    rows.append({'subject': subj.name, 'has_aseg_stats': aseg.exists()})\n"
        "pd.DataFrame(rows)"
    )

@register("fs:aseg_summary")
def fs_aseg_summary(ctx: Dict) -> Iterable[nbf.NotebookNode]:
    root: Path = ctx["dataset_root"]
    yield _md("## aseg.stats summary (toy)")
    yield _code(
        "from pathlib import Path\n"
        "import pandas as pd\n"
        f"root = Path(r'''{root}''')\n"
        "rows = []\n"
        "for subj in sorted([p for p in root.glob('sub-*') if p.is_dir()]):\n"
        "    stats = subj/'stats'/'aseg.stats'\n"
        "    if not stats.exists():\n"
        "        continue\n"
        "    d = {'subject': subj.name}\n"
        "    for line in stats.read_text().splitlines():\n"
        "        if 'BrainSegVol' in line and 'mm^3' in line:\n"
        "            try: d['BrainSegVol'] = float(line.split(',')[2])\n"
        "            except: pass\n"
        "        if 'eTIV' in line and 'mm^3' in line:\n"
        "            try: d['eTIV'] = float(line.split(',')[2])\n"
        "            except: pass\n"
        "    rows.append(d)\n"
        "pd.DataFrame(rows).sort_values('subject') if rows else pd.DataFrame()"
    )




# from __future__ import annotations

# from pathlib import Path
# import os
# import re
# from typing import Dict, Iterable, List

# import nbformat as nbf


# def _md(text: str):
#     return nbf.v4.new_markdown_cell(text)


# def _code(src: str):
#     return nbf.v4.new_code_cell(src)

# def intro_section(dataset_root: Path, generated: str) -> Iterable[nbf.NotebookNode]:
#     yield _md(
#         f"# Dataset Summary (flux-notebooks)\n"
#         f"**Root:** `{dataset_root}`  \n"
#         f"**Generated:** {generated}\n"
#     )


# def init_section(outdir: Path, n_subjects: int, n_sessions: int, n_tasks: int, datatypes: List[str]):
#     css = """
# # from IPython.display import HTML
# # HTML(\"\"\"
# # <style>
# # .jp-Notebook { max-width: 1400px !important; }
# # .jp-Cell .jp-Cell-inputWrapper { max-width: 1400px !important; }
# # table { font-size: 14px; }
# # td { white-space: pre-wrap !important; word-break: break-all !important; }
# # </style>
# # \"\"\")
# """
#     yield _code(css)

#     src = f"""from pathlib import Path
# import json, os, re
# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# import ipywidgets as widgets
# from IPython.display import display, Markdown

# outdir = Path(r'{outdir}')
# avail = pd.read_csv(outdir/'avail.csv') if (outdir/'avail.csv').exists() else None
# func  = pd.read_csv(outdir/'func_counts.csv') if (outdir/'func_counts.csv').exists() else None

# pd.set_option('display.max_colwidth', None)
# plt.rcParams['figure.figsize'] = (10, 4)
# plt.rcParams['figure.dpi'] = 120

# n_subjects={n_subjects}; n_sessions={n_sessions}; n_tasks={n_tasks}; datatypes={datatypes}
# print('Subjects:', n_subjects)
# print('Sessions:', n_sessions)
# print('Tasks:', n_tasks)
# print('Datatypes:', datatypes)
# """
#     yield _code(src)


# def metadata_section(dataset_root: Path):
#     yield _md("## Dataset metadata\nWe try to read `dataset_description.json` and `participants.tsv` if present.")
#     src = f"""from pathlib import Path
# import json
# import pandas as pd
# from IPython.display import display, Markdown

# ds_desc_path = Path(r'{dataset_root}')/'dataset_description.json'
# ds_desc = json.loads(ds_desc_path.read_text()) if ds_desc_path.exists() else {{}}
# display(pd.DataFrame([ds_desc])) if ds_desc else display(Markdown('_No dataset_description.json found._'))

# pt_path = Path(r'{dataset_root}')/'participants.tsv'
# participants = pd.read_csv(pt_path, sep='\\t', dtype=str) if pt_path.exists() else None
# if isinstance(participants, pd.DataFrame):
#     display(participants.head())
#     # quick summaries if age/sex present
#     if any(c.lower().startswith('age') for c in participants.columns):
#         age_col = [c for c in participants.columns if c.lower().startswith('age')][0]
#         with pd.option_context('mode.use_inf_as_na', True):
#             ages = pd.to_numeric(participants[age_col], errors='coerce')
#         display(pd.DataFrame({{'n': [ages.notna().sum()], 'min':[ages.min()], 'median':[ages.median()], 'max':[ages.max()]}}))
#     if any(c.lower() in ('sex','gender') for c in participants.columns):
#         sex_col = [c for c in participants.columns if c.lower() in ('sex','gender')][0]
#         display(participants[sex_col].str.lower().value_counts().rename_axis('sex').to_frame('count'))
# else:
#     display(Markdown('_No participants.tsv found._'))
# """
#     yield _code(src)


# def kpi_section(dataset_root: Path):
#     yield _md("## KPIs")
#     src = f"""# size_by_datatype (best-effort): sum file sizes per top-level datatype folder
# from collections import defaultdict
# import os
# import pandas as pd

# size_by_dt = defaultdict(int)
# try:
#     if isinstance(avail, pd.DataFrame):
#         for dt in avail.columns:
#             dt_dir = Path(r'{dataset_root}')/dt
#             if dt_dir.exists():
#                 for p,_,files in os.walk(dt_dir):
#                     for f in files:
#                         try:
#                             size_by_dt[dt] += (Path(p)/f).stat().st_size
#                         except Exception:
#                             pass
#     size_df = pd.DataFrame({{'datatype': list(size_by_dt.keys()), 'GB': [v/(1024**3) for v in size_by_dt.values()]}})
#     if not size_df.empty:
#         display(size_df.sort_values('GB', ascending=False).reset_index(drop=True))
# except Exception as e:
#     print('Size calc skipped:', e)
# """
#     yield _code(src)


# def availability_section():
#     yield _md("## Subject × datatype availability")
#     src = """import pandas as pd
# import matplotlib.pyplot as plt
# from IPython.display import display

# if isinstance(avail, pd.DataFrame):
#     A = avail.copy()
#     if 'sub' in A.columns:
#         A = A.set_index('sub')
#     display(A)

#     totals = A.sum(axis=0).sort_values(ascending=False)
#     plt.figure(figsize=(max(8, 0.6*len(totals)), 4))
#     totals.plot(kind='bar')
#     plt.ylabel('files'); plt.title('Total files per datatype')
#     plt.tight_layout(); plt.show()

#     per_sub = A.sum(axis=1).sort_values(ascending=False)
#     plt.figure(figsize=(max(8, 0.35*len(per_sub)), 4))
#     per_sub.plot(kind='bar')
#     plt.ylabel('files'); plt.title('Total files per subject')
#     plt.tight_layout(); plt.show()
# else:
#     display('No availability table.')
# """
#     yield _code(src)


# def func_runs_section():
#     yield _md("## Functional runs by task (interactive)")
#     src = """import matplotlib.pyplot as plt
# import ipywidgets as widgets
# from IPython.display import display

# if isinstance(func, pd.DataFrame) and not func.empty:
#     func = func.set_index('subject') if 'subject' in func.columns else func
#     tasks = list(func.columns)
#     task_dd = widgets.Dropdown(options=tasks, description='Task')

#     def _bar(task):
#         s = func[task].sort_values(ascending=False)
#         plt.figure(figsize=(max(10, 0.35*len(s)), 4))
#         s.plot(kind='bar')
#         plt.ylabel('# runs'); plt.title(f'Runs per subject — {task}')
#         plt.tight_layout(); plt.show()

#     out = widgets.interactive_output(_bar, {'task': task_dd})
#     display(task_dd, out)
# else:
#     display('No functional runs found.')
# """
#     yield _code(src)


# def tr_section():
#     yield _md("## Functional TR by task")
#     src = """import pandas as pd
# from IPython.display import display

# tr_csv = outdir/'tr_by_task.csv'
# tr_by_task = pd.read_csv(tr_csv) if tr_csv.exists() else None
# display(tr_by_task if isinstance(tr_by_task, pd.DataFrame) else 'TR table not available in this build.')
# """
#     yield _code(src)


# def explorer_section(dataset_root: Path):
#     """BIDS-aware file explorer with aligned controls, Search/Clear, All/None, and scrollable results."""
#     import nbformat as nbf

#     code = f"""from pathlib import Path
# import os, re
# import pandas as pd
# import ipywidgets as widgets
# from ipywidgets import Layout, GridBox
# from IPython.display import display, Markdown, clear_output, HTML

# # show full paths; we’ll control height via a scrollable wrapper
# pd.set_option('display.max_colwidth', None)

# try:
#     from bids import BIDSLayout
#     layout = BIDSLayout(Path(r'{dataset_root}'), validate=False)
# except Exception as e:
#     layout = None
#     display(Markdown(f"_PyBIDS init failed (fallback to string search): {{str(e)}}_"))

# base = Path(r'{dataset_root}')
# sub_opts  = sorted(layout.get_subjects()) if layout else []
# ses_opts  = sorted(layout.get_sessions()) if layout else []
# task_opts = sorted(layout.get_tasks()) if layout else []
# dt_opts   = sorted(layout.get(return_type='id', target='datatype')) if layout else []
# suf_opts  = sorted(layout.get(return_type='id', target='suffix')) if layout else []

# W_SELECT  = '260px'
# W_SHORT   = '260px'
# DESC_W    = '80px'
# TABLE_HEIGHT = '520px'  # viewport height for the results

# def _select_multi(description, options, rows):
#     w = widgets.SelectMultiple(
#         options=options,
#         rows=min(rows, max(3, len(options))) if options else 3,
#         description=description,
#         layout=Layout(width=W_SELECT),
#         style={{'description_width': DESC_W}},
#     )
#     all_btn  = widgets.Button(description='All',  layout=Layout(width='70px'))
#     none_btn = widgets.Button(description='None', layout=Layout(width='70px'))
#     def set_all(_):  w.value = tuple(w.options)
#     def set_none(_): w.value = ()
#     all_btn.on_click(set_all); none_btn.on_click(set_none)
#     return w, widgets.HBox([all_btn, none_btn], layout=Layout(gap='6px'))

# sub_w,  sub_btns  = _select_multi('subject',  sub_opts, 10)
# ses_w,  ses_btns  = _select_multi('session',  ses_opts,  6)
# task_w, task_btns = _select_multi('task',     task_opts, 6)
# dt_w,   dt_btns   = _select_multi('datatype', dt_opts,   6)
# suf_w,  suf_btns  = _select_multi('suffix',   suf_opts,  6)

# txt_w   = widgets.Text(
#     value='',
#     description='contains',
#     placeholder='e.g. partlycloudy or T1w.json',
#     layout=Layout(width=W_SHORT),
#     style={{'description_width': DESC_W}},
#     continuous_update=False,
# )
# limit_w = widgets.IntSlider(
#     value=200, min=50, max=2000, step=50,
#     description='limit',
#     layout=Layout(width=W_SHORT),
#     style={{'description_width': DESC_W}},
#     continuous_update=False,
# )
# cols_w  = widgets.SelectMultiple(
#     options=['subject','session','task','run','datatype','suffix'],
#     value=('subject','task','datatype','suffix'),
#     description='cols',
#     layout=Layout(width=W_SHORT),
#     style={{'description_width': DESC_W}},
# )

# search_btn = widgets.Button(description='Search', button_style='primary', layout=Layout(width='140px'))
# clear_btn  = widgets.Button(description='Clear all', button_style='warning', layout=Layout(width='140px'))
# out_area   = widgets.Output()

# def run_search(_=None):
#     with out_area:
#         clear_output(wait=True)
#         ents = {{}}
#         if sub_w.value:  ents['subject']  = list(sub_w.value)
#         if ses_w.value:  ents['session']  = list(ses_w.value)
#         if task_w.value: ents['task']     = list(task_w.value)
#         if dt_w.value:   ents['datatype'] = list(dt_w.value)
#         if suf_w.value:  ents['suffix']   = list(suf_w.value)

#         try:
#             if layout:
#                 paths = layout.get(return_type='file', **ents)
#             else:
#                 paths = []
#                 for p,_,fs in os.walk(base):
#                     for f in fs:
#                         paths.append(os.path.join(p, f))
#         except Exception as e:
#             display(Markdown(f"_Query error: {{str(e)}}_"))
#             return

#         contains = txt_w.value.strip()
#         if contains:
#             tokens = [t.lower() for t in re.split(r"\\s+", contains) if t]
#             def ok(s):
#                 s = s.lower()
#                 return all(t in s for t in tokens)
#             paths = [p for p in paths if ok(p)]

#         paths = sorted(set(paths))[: int(limit_w.value)]
#         if not paths:
#             display(Markdown('_No matches._')); return

#         rows = []
#         for p in paths:
#             rel = os.path.relpath(p, base)
#             row = {{'path': rel}}
#             if layout:
#                 e = layout.parse_file_entities(p)
#                 for k in ('subject','session','task','run','datatype','suffix'):
#                     if k in e: row[k] = e[k]
#             rows.append(row)

#         df = pd.DataFrame(rows)
#         ordered = ['path'] + [c for c in cols_w.value if c in df.columns]
#         df = df[ordered + [c for c in df.columns if c not in ordered]]

#         # Scrollable, non-truncated HTML wrapper (avoid outer f-string interpolation)
#         html = df.to_html(index=False, escape=False, max_rows=None, max_cols=None)
#         display(HTML(
#             "<div style='max-height:" + TABLE_HEIGHT + "; overflow:auto; width:100%;"
#             " border:1px solid #ddd; border-radius:6px; padding:6px;'>" +
#             html +
#             "</div>"
#         ))

# def clear_all(_):
#     sub_w.value = (); ses_w.value = (); task_w.value = ()
#     dt_w.value  = (); suf_w.value = (); txt_w.value  = ''
#     run_search()

# search_btn.on_click(run_search)
# clear_btn.on_click(clear_all)
# txt_w.observe(lambda ch: run_search() if ch['name']=='value' and ch['type']=='change' else None, names='value')

# grid = GridBox(children=[
#     sub_w,  ses_w,  task_w,
#     sub_btns, ses_btns, task_btns,
#     dt_w,    suf_w,  widgets.VBox([widgets.HBox([txt_w, limit_w], layout=Layout(gap='12px')), cols_w]),
#     dt_btns, suf_btns, widgets.HBox([search_btn, clear_btn], layout=Layout(gap='12px')),
# ], layout=Layout(
#     grid_template_columns='repeat(3, 260px)',
#     grid_gap='10px 20px',
#     align_items='flex-start',
#     width='100%',
# ))

# display(grid, out_area)
# run_search()
# """
#     return [
#         nbf.v4.new_markdown_cell("## Explore files (BIDS explorer + substring search)"),
#         nbf.v4.new_code_cell(code),
#     ]
