# pages/redcap.py
import dash
from dash import html, dcc
from pathlib import Path
import os
from flux_notebooks.redcap.summarize_redcap import summarize_redcap

dash.register_page(__name__, path="/redcap", name="REDCap Summary")

# --- Load data root ---
dataset_root = Path(os.environ.get("FLUX_REDCAP_ROOT", "data/redcap")).resolve()
summary = summarize_redcap(dataset_root)


layout = html.Div(
    style={"fontFamily": "sans-serif", "margin": "20px"},
    children=[
        html.H1("REDCap Summary"),
        html.P("Multi-site participant demographics and recruitment targets."),
        html.Div([
            dcc.Graph(figure=summary["figures"]["age"]),
            dcc.Graph(figure=summary["figures"]["sex"]),
            dcc.Graph(figure=summary["figures"]["totals"]),
        ])
    ]
)




# # src/flux_notebooks/redcap/summarize_redcap.py
# """
# Summarize REDCap multi-site exports (Calgary, Montreal, Toronto).

# - Reads per-site REDCap CSVs (raw exports) from a folder.
# - Deduplicates baseline rows (one T1 row per participant: most key fields).
# - Derives age (years), age blocks, sex, gender, income labels, ethnicity long & white/non-white.
# - Builds Plotly figures equivalent to the matplotlib dashboard panels.
# - Optionally reads target *age_by_group* CSVs for overlays (if present in the same folder).

# Return:
#     {
#       "tables": { ... pandas.DataFrame ... },
#       "figures": { "age": go.Figure, "sex": go.Figure, ... }
#     }

# Usage in Dash:
#     from flux_notebooks.redcap.summarize_redcap import summarize_redcap
#     out = summarize_redcap(Path("/path/to/data/redcap"))
#     out["figures"]["age"]  # -> plotly figure
# """

# from pathlib import Path
# from typing import Optional, List, Dict, Tuple
# import re
# from datetime import datetime

# import numpy as np
# import pandas as pd
# import plotly.express as px
# import plotly.graph_objects as go


# # ───────────────────────── CONFIG ─────────────────────────
# SITE_ORDER   = ["Calgary", "Montreal", "Toronto"]
# SITE_COLOURS = {"Montreal": "#1f77b4", "Calgary": "#ff0e0e", "Toronto": "#2ca02c"}

# MIN_T1_DATE    = pd.Timestamp("2023-01-01")
# MRI_INSTRUMENT = "mri"  # lower-case

# # Fixed hue order + colors for Target vs Observed overlays
# MEASURE_ORDER   = ["Target", "Observed"]
# MEASURE_COLOURS = {"Target": "#f58518", "Observed": "#4c78a8"}

# # Ethnicity order for consistent axes (collapsed bins where used)
# ETHNICITY_ORDER_TARGET = ["White", "Asian", "Black", "Indigenous", "Middle East", "Latin American", "Other"]

# # Age-bin labels used in target CSV parsing (first bin renamed to "<5wks")
# AGE_BIN_ORDER = ["<5wks"] + [f"{i}-{i+1}" for i in range(0, 18)] + ["18"]

# # For age-block panels
# AGE_BLOCK_ORDER = ["0-2", "2-5", "6-9", "10-12", "13-15", "16-18"]

# # Target totals (unchanged)
# TARGET_TOTALS = {
#     "Calgary": {
#         "Total": 263,
#         "Sex": {"Male":132, "Female":132},
#         "Ethnicity": {"White":153,"Asian":63,"Black":11,"Indigenous":8,"Middle East":8,"Latin American":5,"Other":16},
#         "UrbanRural": {"Urban":213,"Rural":50},
#         "SES": {"MidHigh":223,"Low":41},
#     },
#     "Toronto": {
#         "Total": 263,
#         "Sex": {"Male":132, "Female":132},
#         "Ethnicity": {"White":124,"Asian":87,"Black":24,"Indigenous":3,"Middle East":11,"Latin American":8,"Other":8},
#         "UrbanRural": {"Urban":226,"Rural":37},
#         "SES": {"MidHigh":201,"Low":63},
#     },
#     "Montreal": {
#         "Total": 263,
#         "Sex": {"Male":132, "Female":132},
#         "Ethnicity": {"White":171,"Asian":29,"Black":26,"Indigenous":3,"Middle East":21,"Latin American":11,"Other":3},
#         "UrbanRural": {"Urban":211,"Rural":53},
#         "SES": {"MidHigh":183,"Low":80},
#     }
# }

# # CFQ mental-health variables and labels
# CFQ_VARS = [
#     "cfq_diag_asd_part","cfq_diag_id_part","cfq_adhd_part","cfq_fasd_part",
#     "cfq_ld_part","cfq_lcd_part","cfq_md_part","cfq_diag_other_part",
#     "cfq_ment_ad_part","cfq_ment_dd_part","cfq_ment_bd_part","cfq_ment_ocd_part",
#     "cfq_ment_ts_part","cfq_ment_psyep_part","cfq_ment_schizo_part",
#     "cfq_ment_sa_part","cfq_ment_epilepsy_part","cfq_ment_other_part"
# ]
# CFQ_LABELS = {
#     "cfq_diag_asd_part": "Autism Spectrum Disorder",
#     "cfq_diag_id_part": "Cognitive Impair/IDD",
#     "cfq_adhd_part": "ADHD",
#     "cfq_fasd_part": "FASD",
#     "cfq_ld_part": "Learning Disability",
#     "cfq_lcd_part": "Language Disorder",
#     "cfq_md_part": "Motor Disorder",
#     "cfq_diag_other_part": "Other Neurodev.",
#     "cfq_ment_ad_part": "Anxiety Disorder",
#     "cfq_ment_dd_part": "Depressive Disorder",
#     "cfq_ment_bd_part": "Bipolar Disorder",
#     "cfq_ment_ocd_part": "OCD",
#     "cfq_ment_ts_part": "Tourette’s",
#     "cfq_ment_psyep_part": "Psychosis",
#     "cfq_ment_schizo_part": "Schizophrenia",
#     "cfq_ment_sa_part": "Substance Abuse",
#     "cfq_ment_epilepsy_part": "Epilepsy",
#     "cfq_ment_other_part": "Other (MH)"
# }

# SEX_MAP    = {1:"Male",2:"Female",3:"Intersex / Non-binary",777:"Unknown",888:"Prefer not to answer", np.nan:"NA"}
# GENDER_MAP = {1:"Boy/Man",2:"Girl/Woman",3:"Non-binary",4:"Two-spirit",5:"Another",
#               6:"Questioning",777:"Unknown",888:"Prefer not to answer", np.nan:"NA"}
# INCOME_MAP = {1:"Under $10k",2:"$10-19k",3:"$20-39k",4:"$40-59k",5:"$60-79k",
#               6:"$80-99k",7:"$100-124k",8:"$125-149k",9:"$150-199k",
#               10:"$200-299k",11:"$300-399k",12:"$400k+",777:"Unknown",888:"Prefer not to say"}

# # Income merge helpers
# _BRACKET_MEDIAN = {
#      1:   5_000,  2:  15_000,  3:  30_000,  4:  50_000,
#      5:  70_000,  6:  90_000,  7: 112_500,  8: 137_500,
#      9: 175_000, 10: 250_000, 11: 350_000, 12: 450_000
# }
# _SPECIAL_INCOME = {777, 888}

# ASIAN = {"East Asian","South Asian","Southeast Asian"}
# INDIG = {"First Nations","Inuk/Inuit","Métis"}


# # ───────────────────────── HELPERS ────────────────────────
# def derive_site(p: Path) -> str:
#     s = p.stem.lower()
#     if "montreal" in s: return "Montreal"
#     if "calgary"  in s: return "Calgary"
#     if "toronto"  in s: return "Toronto"
#     raise ValueError(f"Cannot infer site from filename: {p.name}")


# def load_site_csvs(folder: Path) -> pd.DataFrame:
#     """
#     Load site REDCap CSV exports in `folder`, attach 'site', concatenate.
#     Expected filenames contain 'montreal' / 'calgary' / 'toronto'.
#     """
#     files = [p for p in folder.glob("*.csv") if any(k in p.name.lower() for k in ("montreal","calgary","toronto"))]
#     if not files:
#         raise FileNotFoundError(f"No site CSVs found in {folder}")
#     dfs = []
#     for f in files:
#         site = derive_site(f)
#         df = pd.read_csv(f, low_memory=False)
#         df["site"] = site
#         dfs.append(df)
#     return pd.concat(dfs, ignore_index=True)


# def pick_first(df: pd.DataFrame, names: List[str], *, required=False) -> Optional[str]:
#     for n in names:
#         if n in df.columns:
#             return n
#     if required:
#         raise ValueError(f"None of {names} found in columns")
#     return None


# def _as_int_or_nan(x):
#     try:
#         return int(x)
#     except Exception:
#         return np.nan


# def merge_income_row(row: pd.Series) -> float:
#     cg = _as_int_or_nan(row.get("demo_cg_income"))
#     pt = _as_int_or_nan(row.get("demo_cg_prtnr_income"))
#     if cg in _SPECIAL_INCOME: return cg
#     if pt in _SPECIAL_INCOME: return pt
#     if pd.isna(cg) and pd.isna(pt): return np.nan
#     if pd.isna(pt): return cg
#     if pd.isna(cg): return pt
#     total = _BRACKET_MEDIAN[int(cg)] + _BRACKET_MEDIAN[int(pt)]
#     # round total back to nearest bracket code
#     return int(min(_BRACKET_MEDIAN, key=lambda c: abs(_BRACKET_MEDIAN[c] - total)))


# def _age_years(row: pd.Series) -> float:
#     y, m = row.get("youth_age_y"), row.get("youth_age_m")
#     if pd.isna(y) and pd.isna(m): return np.nan
#     return (0 if pd.isna(y) else y) + (0 if pd.isna(m) else m) / 12


# def to_age_block(a: float) -> Optional[str]:
#     if pd.isna(a): return None
#     if a <= 2:   return "0-2"
#     if a <= 5:   return "2-5"
#     if a <= 9:   return "6-9"
#     if a <= 12:  return "10-12"
#     if a <= 15:  return "13-15"
#     if a <= 18:  return "16-18"
#     return None


# def bin_label_to_block(lbl: str) -> Optional[str]:
#     if lbl is None: return None
#     if lbl == "<5wks": return None
#     if lbl == "18": return "16-18"
#     m = re.match(r"^(\d+)-(\d+)$", str(lbl))
#     if not m: return None
#     k = int(m.group(1))
#     if k < 2:   return "0-2"
#     if k < 6:   return "2-5"
#     if k < 10:  return "6-9"
#     if k < 13:  return "10-12"
#     if k < 16:  return "13-15"
#     return "16-18"


# def _collapse_eth(lbl: str) -> Optional[str]:
#     if lbl in ASIAN: return "Asian"
#     if lbl in INDIG: return "Indigenous"
#     if lbl == "Middle Eastern": return "Middle East"
#     if lbl in {"Black","Middle East","Latin American","Other","White"}: return lbl
#     return None


# def _load_targets_age_by_group(folder: Path) -> pd.DataFrame:
#     """
#     Returns long DF with columns: site, Group, age_bin_label, Target_N
#     Reads *age_by_group*.csv files if present (optional).
#     """
#     rows = []
#     for stem in ("calgary", "montreal", "toronto"):
#         ps = list(folder.glob(f"*{stem}*age_by_group*.csv"))
#         if not ps:
#             continue
#         p = ps[0]
#         site = derive_site(p)
#         t = pd.read_csv(p, comment="#")
#         t = t.rename(columns={"5 wks pre": "<5wks"})
#         keep_cols = ["Group"] + AGE_BIN_ORDER + ["Total"]
#         cols = [c for c in keep_cols if c in t.columns]
#         if "Group" not in cols:
#             continue
#         t = t[cols].copy()
#         value_cols = [c for c in AGE_BIN_ORDER if c in t.columns]
#         long = t.melt(id_vars=["Group"], value_vars=value_cols,
#                       var_name="age_bin_label", value_name="Target_N")
#         long["site"] = site
#         long["Group"] = long["Group"].replace({"Middle Eastern": "Middle East"})
#         rows.append(long[["site","Group","age_bin_label","Target_N"]])
#     if not rows:
#         return pd.DataFrame(columns=["site","Group","age_bin_label","Target_N"])
#     out = pd.concat(rows, ignore_index=True)
#     out["Target_N"] = pd.to_numeric(out["Target_N"], errors="coerce").fillna(0.0)
#     out["age_bin_label"] = pd.Categorical(out["age_bin_label"], categories=AGE_BIN_ORDER, ordered=True)
#     return out


# # ───────────────────────── MAIN SUMMARIZER ────────────────────────
# def summarize_redcap(folder: Path) -> Dict[str, Dict[str, object]]:
#     """
#     Build tables and Plotly figures replicating the dashboard script.

#     Args:
#         folder: Path to directory containing REDCap site CSVs (and optionally *age_by_group*.csv targets)

#     Returns:
#         {"tables": {...}, "figures": {...}}
#     """
#     # Load & filter to non-repeating rows
#     df_main = load_site_csvs(folder)
#     non_repeat = df_main[df_main.get("redcap_repeat_instrument").isna()].copy()

#     # Key column discovery
#     sex_col    = pick_first(non_repeat, ["sex", "demo_sex"], required=True)
#     gender_col = pick_first(non_repeat, ["gender", "demo_gender", "gender_oth"], required=True)
#     eth_cols   = [c for c in non_repeat.columns if re.match(r"(demo_)?ethnicity___\d+", c)]

#     # Income merge
#     if {"demo_cg_income", "demo_cg_prtnr_income"} & set(non_repeat.columns):
#         non_repeat["demo_cg_income"] = non_repeat.apply(merge_income_row, axis=1)
#     elif "demo_cg_prtnr_income" in non_repeat.columns:
#         non_repeat["demo_cg_income"] = non_repeat["demo_cg_prtnr_income"].apply(_as_int_or_nan)
#     else:
#         non_repeat["demo_cg_income"] = non_repeat.get("demo_cg_income", np.nan).apply(_as_int_or_nan)

#     # Pick best T1 row per participant
#     key_vars = ["youth_age_y", "youth_age_m", sex_col, gender_col, "demo_cg_income"] + eth_cols
#     t1 = non_repeat[non_repeat["redcap_event_name"] == "t1_arm_1"].copy()
#     t1["_score"] = t1[key_vars].notna().sum(axis=1)
#     t1 = t1.sort_values(["record_id", "_score"], ascending=[True, False])
#     baseline = t1.drop_duplicates(subset="record_id").drop(columns="_score").reset_index(drop=True)

#     # Derived fields
#     baseline["age_years"]  = baseline.apply(_age_years, axis=1)
#     baseline["sex_lbl"]    = baseline[sex_col].map(SEX_MAP)
#     baseline["gender_lbl"] = baseline[gender_col].map(GENDER_MAP)
#     baseline["income_lbl"] = baseline["demo_cg_income"].map(INCOME_MAP)

#     # Ethnicity (checkbox melt)
#     if eth_cols:
#         baseline[eth_cols] = baseline[eth_cols].fillna(0)
#         eth_lookup = {f"{p}{i}": lbl
#                       for p in ("demo_ethnicity___","demo_cg_ethnicity___")
#                       for i,lbl in {
#                           1:"Black",2:"East Asian",3:"First Nations",4:"Inuk/Inuit",5:"Métis",
#                           6:"Latin American",7:"Middle Eastern",8:"South Asian",9:"Southeast Asian",
#                           10:"White",11:"Other",888:"Prefer not to say"}.items()}
#         eth_long = (baseline[["record_id","site"] + eth_cols]
#                     .melt(id_vars=["record_id","site"], value_name="val")
#                     .query("val == 1")
#                     .assign(label=lambda d: d["variable"].map(eth_lookup)))
#     else:
#         eth_long = pd.DataFrame(columns=["record_id","site","variable","val","label"])

#     # White vs Non-white wide (for one panel)
#     eth_wide = pd.DataFrame(columns=["site","record_id","White","Non-white"])
#     if not eth_long.empty:
#         tmp = (eth_long.groupby(["site","record_id"])["label"]
#                .apply(lambda s: sorted(set(s.dropna()))).reset_index(name="labels"))
#         tmp["is_white_only"] = tmp["labels"].apply(lambda L: ("White" in set(L)) and (len(set(L))==1))
#         tmp["has_nonwhite"]  = tmp["labels"].apply(lambda L: any(l!="White" for l in set(L)))
#         eth_wide = tmp[["site","record_id","is_white_only","has_nonwhite"]].copy()
#         eth_wide["White"] = eth_wide["is_white_only"].map({True:"White", False:np.nan})
#         eth_wide["Non-white"] = eth_wide["has_nonwhite"].map({True:"Non-white", False:np.nan})
#         eth_wide = eth_wide[["site","record_id","White","Non-white"]]

#     # MRI baseline timeline (deduped)
#     mri_base = df_main.loc[
#         (df_main.get("redcap_event_name") == "t1_arm_1") &
#         (df_main.get("redcap_repeat_instrument", "").fillna("").str.strip().str.lower() == MRI_INSTRUMENT)
#     ].copy()
#     mri_base["mri_date"] = pd.to_datetime(mri_base.get("mri_date"), errors="coerce").dt.normalize()
#     if "record_id" in mri_base.columns:
#         mri_base = (mri_base.dropna(subset=["mri_date"])
#                             .loc[mri_base["mri_date"] >= MIN_T1_DATE]
#                             .sort_values("mri_complete", ascending=False)
#                             .drop_duplicates(subset=["record_id","mri_date"]))
#         sched = (mri_base.groupby(["site","mri_date"])["record_id"].nunique()
#                          .groupby(level=0).cumsum().rename("cum").reset_index().assign(status="Scheduled"))
#         comp  = (mri_base[mri_base.get("mri_complete") == 2]
#                  .groupby(["site","mri_date"])["record_id"].nunique()
#                  .groupby(level=0).cumsum().rename("cum").reset_index().assign(status="Completed"))
#         timeline = pd.concat([sched, comp], ignore_index=True)
#     else:
#         timeline = pd.DataFrame(columns=["site","mri_date","cum","status"])

#     # Sanity-check counts & NA counts
#     def _count_non_na(col: str) -> pd.Series:
#         return (baseline[baseline[col].notna()].groupby("site")["record_id"].nunique())

#     site_totals = baseline.groupby("site")["record_id"].nunique()
#     counts = pd.DataFrame({
#         "Total available counts": site_totals,
#         "Age non-NA":     _count_non_na("age_years"),
#         "Sex non-NA":     _count_non_na("sex_lbl"),
#         "Gender non-NA":  _count_non_na("gender_lbl"),
#         "Income non-NA":  _count_non_na("income_lbl"),
#     })
#     if not eth_long.empty:
#         eth_non_na = eth_long.groupby("site")["record_id"].nunique().rename("Ethnicity non-NA")
#         counts = counts.join(eth_non_na, how="left")
#     else:
#         eth_non_na = pd.Series(0, index=site_totals.index, name="Ethnicity non-NA")

#     counts = counts.fillna(0).astype(int)

#     na_counts = pd.DataFrame({
#         "Total available counts": site_totals,
#         "Age NA":      (site_totals - _count_non_na("age_years")),
#         "Sex NA":      (site_totals - _count_non_na("sex_lbl")),
#         "Gender NA":   (site_totals - _count_non_na("gender_lbl")),
#         "Income NA":   (site_totals - _count_non_na("income_lbl")),
#         "Ethnicity NA": (site_totals - eth_non_na.reindex(site_totals.index).fillna(0).astype(int)),
#     }).fillna(0).astype(int)

#     # ────────── Plot data preps ──────────
#     # Age blocks
#     age_block_counts = (
#         baseline.assign(age_block=lambda d: d["age_years"].apply(to_age_block))
#                 .dropna(subset=["age_block"])
#                 .groupby(["site","age_block"])["record_id"].nunique()
#                 .reset_index(name="Count")
#     )
#     # Ethnicity panel (full labels order by frequency)
#     if not eth_long.empty:
#         order_eth_full = eth_long["label"].value_counts().index.tolist()
#         eth_counts_panel = (eth_long.groupby(["site","label"])["record_id"]
#                             .nunique().reset_index(name="Count"))
#         eth_counts_panel["label"] = pd.Categorical(eth_counts_panel["label"],
#                                                    categories=order_eth_full, ordered=True)
#     else:
#         order_eth_full = []
#         eth_counts_panel = pd.DataFrame(columns=["site","label","Count"])

#     # White/Non-white counts
#     if not eth_wide.empty:
#         eth_wide_long = (eth_wide.melt(id_vars=["site","record_id"],
#                                        value_vars=["White","Non-white"],
#                                        var_name="Ethnicity", value_name="Label")
#                          .dropna(subset=["Label"]))
#         eth_wnw_counts = (eth_wide_long.groupby(["site","Ethnicity"])["record_id"]
#                           .nunique().reset_index(name="Count"))
#     else:
#         eth_wnw_counts = pd.DataFrame(columns=["site","Ethnicity","Count"])

#     # Income order
#     order_inc = [INCOME_MAP[i] for i in range(1, 13)] + [INCOME_MAP[777], INCOME_MAP[888]]

#     # NA counts long
#     if not na_counts.empty:
#         na_counts_long = (na_counts.reset_index()
#             .rename(columns={"index":"site"})
#             .melt(id_vars="site", var_name="Metric", value_name="Count"))
#         metric_order = ["Total available counts", "Age NA", "Sex NA", "Gender NA",
#                         "Income NA", "Ethnicity NA"]
#         na_counts_long["Metric"] = pd.Categorical(na_counts_long["Metric"],
#                                                   categories=metric_order, ordered=True)
#     else:
#         na_counts_long = pd.DataFrame(columns=["site","Metric","Count"])

#     # Targets for overlays (optional)
#     targets_age_group = _load_targets_age_by_group(folder)

#     # Observed: Sex × Age blocks (Male/Female only)
#     obs_sex_age_blocks = (
#         baseline.dropna(subset=["sex_lbl","age_years"])
#                 .assign(age_block=lambda d: d["age_years"].apply(to_age_block))
#                 .dropna(subset=["age_block"])
#                 .query("sex_lbl in ['Male','Female']")
#                 .groupby(["site","sex_lbl","age_block"])["record_id"]
#                 .nunique().reset_index(name="Observed_N")
#     )

#     # Observed: Ethnicity × Age (collapsed + white-only logic)
#     white_only_df = pd.DataFrame(columns=["record_id","site","age_years","Ethnicity","age_block"])
#     nonwhite = pd.DataFrame(columns=["site","record_id","Ethnicity","age_block"])
#     if not eth_long.empty:
#         by_rec = (eth_long.groupby(["site","record_id"])["label"]
#                   .apply(lambda s: sorted(set(s.dropna()))).reset_index(name="labels"))

#         white_ids = set(by_rec.loc[
#             by_rec["labels"].apply(lambda L: ("White" in set(L)) and (len(set(L))==1)),
#             "record_id"
#         ])
#         white_only_df = (baseline.loc[baseline["record_id"].isin(white_ids),
#                                       ["record_id","site","age_years"]]
#                          .assign(Ethnicity="White",
#                                  age_block=lambda d: d["age_years"].apply(to_age_block)))

#         nonwhite = by_rec.loc[by_rec["labels"].apply(lambda L: any(l!="White" for l in set(L)))].copy()
#         nonwhite = (nonwhite.assign(EthnicityList=nonwhite["labels"].apply(lambda L: [l for l in L if l!="White"]))
#                             .explode("EthnicityList")
#                             .rename(columns={"EthnicityList":"Ethnicity"})
#                             .drop(columns="labels"))
#         nonwhite["Ethnicity"] = nonwhite["Ethnicity"].map(_collapse_eth)
#         nonwhite = nonwhite.dropna(subset=["Ethnicity"])
#         nonwhite = (nonwhite.merge(baseline[["record_id","age_years","site"]], on=["record_id","site"], how="left")
#                             .assign(age_block=lambda d: d["age_years"].apply(to_age_block)))

#     parts = []
#     if not white_only_df.empty:
#         parts.append(white_only_df[["site","Ethnicity","age_block","record_id"]])
#     if not nonwhite.empty:
#         parts.append(nonwhite[["site","Ethnicity","age_block","record_id"]])
#     if parts:
#         obs_eth_age_blocks = (pd.concat(parts, ignore_index=True)
#                               .dropna(subset=["age_block"])
#                               .groupby(["site","Ethnicity","age_block"])["record_id"]
#                               .nunique().reset_index(name="Observed_N"))
#     else:
#         obs_eth_age_blocks = pd.DataFrame(columns=["site","Ethnicity","age_block","Observed_N"])

#     # For totals comparison
#     obs_eth_tot = pd.DataFrame(columns=["site","Ethnicity","Observed_N"])
#     if not eth_long.empty:
#         by_rec2 = eth_long.copy()
#         by_rec2["Ethnicity"] = by_rec2["label"].map(_collapse_eth)
#         by_rec2 = by_rec2.dropna(subset=["Ethnicity"])

#         white_tot = pd.DataFrame(columns=["site","record_id","Ethnicity"])
#         if not white_only_df.empty:
#             white_tot = white_only_df[["site","record_id"]].assign(Ethnicity="White")
#         nonwhite_tot = by_rec2[by_rec2["Ethnicity"]!="White"][["site","record_id","Ethnicity"]].drop_duplicates()

#         obs_all = pd.concat([white_tot, nonwhite_tot], ignore_index=True)
#         obs_eth_tot = (obs_all.groupby(["site","Ethnicity"])["record_id"]
#                        .nunique().reset_index(name="Observed_N"))

#     # Build targets totals DF
#     targ_rows = []
#     for site, payload in TARGET_TOTALS.items():
#         for eth, n in payload["Ethnicity"].items():
#             targ_rows.append({"site":site, "Ethnicity":eth, "Target_N": int(n)})
#     targets_tot_eth = pd.DataFrame(targ_rows)

#     # ────────── Figures (Plotly) ──────────
#     figs: Dict[str, go.Figure] = {}

#     # Age groups by site (baseline, blocks)
#     if not age_block_counts.empty:
#         age_block_counts["age_block"] = pd.Categorical(age_block_counts["age_block"],
#                                                        categories=AGE_BLOCK_ORDER, ordered=True)
#         figs["age"] = px.bar(
#             age_block_counts, x="age_block", y="Count", color="site",
#             category_orders={"site": SITE_ORDER, "age_block": AGE_BLOCK_ORDER},
#             color_discrete_map=SITE_COLOURS,
#             title="Age groups by site (baseline)"
#         )
#     else:
#         figs["age"] = go.Figure()

#     # Sex assigned at birth (baseline)
#     if not baseline.empty:
#         sex_counts = (baseline.groupby(["site","sex_lbl"])["record_id"]
#                       .nunique().reset_index(name="Count"))
#         figs["sex"] = px.bar(
#             sex_counts, x="sex_lbl", y="Count", color="site",
#             category_orders={"site": SITE_ORDER},
#             color_discrete_map=SITE_COLOURS, title="Sex assigned at birth (baseline)"
#         )
#     else:
#         figs["sex"] = go.Figure()

#     # Gender identity
#     if not baseline.empty:
#         order_g = ["Boy/Man","Girl/Woman","Non-binary","Two-spirit","Another",
#                    "Questioning","Unknown","Prefer not to answer","NA"]
#         gender_counts = (baseline.groupby(["site","gender_lbl"])["record_id"]
#                          .nunique().reset_index(name="Count"))
#         gender_counts["gender_lbl"] = pd.Categorical(gender_counts["gender_lbl"], categories=order_g, ordered=True)
#         figs["gender"] = px.bar(
#             gender_counts, x="gender_lbl", y="Count", color="site",
#             category_orders={"site": SITE_ORDER, "gender_lbl": order_g},
#             color_discrete_map=SITE_COLOURS, title="Current gender identity (baseline)"
#         )
#     else:
#         figs["gender"] = go.Figure()

#     # Ethnicity (full labels)
#     if not eth_counts_panel.empty:
#         figs["ethnicity_full"] = px.bar(
#             eth_counts_panel, x="label", y="Count", color="site",
#             category_orders={"site": SITE_ORDER, "label": order_eth_full},
#             color_discrete_map=SITE_COLOURS, title="Ethnicity (baseline)"
#         )
#     else:
#         figs["ethnicity_full"] = go.Figure()

#     # Ethnicity (White / Non-white)
#     if not eth_wnw_counts.empty:
#         figs["ethnicity_white_nonwhite"] = px.bar(
#             eth_wnw_counts, x="Ethnicity", y="Count", color="site",
#             category_orders={"site": SITE_ORDER, "Ethnicity": ["White","Non-white"]},
#             color_discrete_map=SITE_COLOURS, title="Ethnicity (White/Non-white) by site"
#         )
#     else:
#         figs["ethnicity_white_nonwhite"] = go.Figure()

#     # Income
#     inc_non_na = baseline.dropna(subset=["income_lbl"])
#     if not inc_non_na.empty:
#         inc_counts = (inc_non_na.groupby(["site","income_lbl"])["record_id"]
#                       .nunique().reset_index(name="Count"))
#         inc_counts["income_lbl"] = pd.Categorical(inc_counts["income_lbl"], categories=order_inc, ordered=True)
#         figs["income"] = px.bar(
#             inc_counts, x="income_lbl", y="Count", color="site",
#             category_orders={"site": SITE_ORDER, "income_lbl": order_inc},
#             color_discrete_map=SITE_COLOURS, title="Household income (baseline)"
#         )
#     else:
#         figs["income"] = go.Figure()

#     # Missing counts per panel
#     if not na_counts_long.empty:
#         figs["missing_counts"] = px.bar(
#             na_counts_long, x="Metric", y="Count", color="site",
#             category_orders={"site": SITE_ORDER},
#             color_discrete_map=SITE_COLOURS, title="Missing counts per panel"
#         )
#     else:
#         figs["missing_counts"] = go.Figure()

#     # MRI timeline (cumulative)
#     if not timeline.empty:
#         figs["mri_timeline"] = px.line(
#             timeline, x="mri_date", y="cum", color="site", line_dash="status",
#             category_orders={"site": SITE_ORDER},
#             color_discrete_map=SITE_COLOURS, title="Baseline MRI visits by site"
#         )
#     else:
#         figs["mri_timeline"] = go.Figure()

#     # ────────── Overlays: Observed vs Target — Age × Sex (blocks) ──────────
#     if not targets_age_group.empty and not obs_sex_age_blocks.empty:
#         targ_sex = targets_age_group[targets_age_group["Group"].isin(["Male","Female"])].copy()
#         targ_sex["age_block"] = targ_sex["age_bin_label"].map(bin_label_to_block)
#         targ_sex = (targ_sex.dropna(subset=["age_block"])
#                            .groupby(["site","Group","age_block"])["Target_N"]
#                            .sum().reset_index()
#                            .rename(columns={"Group":"sex_lbl"}))
#         sx_obs = obs_sex_age_blocks.rename(columns={"Observed_N":"N"}).assign(Measure="Observed")
#         sx_tgt = targ_sex.rename(columns={"Target_N":"N"}).assign(Measure="Target")
#         sx_long = pd.concat([sx_tgt, sx_obs], ignore_index=True)
#         sx_long["age_block"] = pd.Categorical(sx_long["age_block"], categories=AGE_BLOCK_ORDER, ordered=True)

#         figs["overlay_age_sex"] = px.bar(
#             sx_long, x="age_block", y="N",
#             facet_col="site", facet_row="sex_lbl",
#             color="Measure", category_orders={"site": SITE_ORDER, "age_block": AGE_BLOCK_ORDER, "Measure": MEASURE_ORDER},
#             color_discrete_map=MEASURE_COLOURS, barmode="group",
#             title="Observed vs Target by Age × Sex, per site"
#         )
#     else:
#         figs["overlay_age_sex"] = go.Figure()

#     # ────────── Overlays: Observed vs Target — Age × Ethnicity (blocks) ──────────
#     if not targets_age_group.empty and not obs_eth_age_blocks.empty:
#         targ_eth = targets_age_group[targets_age_group["Group"].isin(ETHNICITY_ORDER_TARGET)].copy()
#         targ_eth["age_block"] = targ_eth["age_bin_label"].map(bin_label_to_block)
#         targ_eth = (targ_eth.dropna(subset=["age_block"])
#                            .groupby(["site","Group","age_block"])["Target_N"]
#                            .sum().reset_index()
#                            .rename(columns={"Group":"Ethnicity"}))
#         et_obs = obs_eth_age_blocks.rename(columns={"Observed_N":"N"}).assign(Measure="Observed")
#         et_tgt = targ_eth.rename(columns={"Target_N":"N"}).assign(Measure="Target")
#         et_long = pd.concat([et_tgt, et_obs], ignore_index=True)
#         et_long["Ethnicity"] = pd.Categorical(et_long["Ethnicity"], categories=ETHNICITY_ORDER_TARGET, ordered=True)
#         et_long["age_block"] = pd.Categorical(et_long["age_block"], categories=AGE_BLOCK_ORDER, ordered=True)

#         figs["overlay_age_ethnicity"] = px.bar(
#             et_long, x="age_block", y="N",
#             facet_col="site", facet_row="Ethnicity",
#             color="Measure",
#             category_orders={"site": SITE_ORDER, "age_block": AGE_BLOCK_ORDER,
#                              "Ethnicity": ETHNICITY_ORDER_TARGET, "Measure": MEASURE_ORDER},
#             color_discrete_map=MEASURE_COLOURS, barmode="group",
#             title="Observed vs Target by Age × Ethnicity, per site"
#         )
#     else:
#         figs["overlay_age_ethnicity"] = go.Figure()

#     # ────────── Overlays: Observed vs Target — Ethnicity totals ──────────
#     if not obs_eth_tot.empty:
#         compare_df = (targets_tot_eth.merge(obs_eth_tot, on=["site","Ethnicity"], how="left")
#                                     .fillna({"Observed_N":0}).astype({"Observed_N":int}))
#         compare_df["Ethnicity"] = pd.Categorical(compare_df["Ethnicity"],
#                                                  categories=ETHNICITY_ORDER_TARGET, ordered=True)
#         cmp_long = pd.concat([
#             compare_df.rename(columns={"Target_N":"N"})[["site","Ethnicity","N"]].assign(Measure="Target"),
#             compare_df.rename(columns={"Observed_N":"N"})[["site","Ethnicity","N"]].assign(Measure="Observed")
#         ], ignore_index=True)

#         figs["overlay_ethnicity_totals"] = px.bar(
#             cmp_long, x="Ethnicity", y="N", color="Measure",
#             facet_col="site",
#             category_orders={"site": SITE_ORDER, "Ethnicity": ETHNICITY_ORDER_TARGET, "Measure": MEASURE_ORDER},
#             color_discrete_map=MEASURE_COLOURS, barmode="group",
#             title="Observed vs Target recruitment by Ethnicity and Site"
#         )
#     else:
#         figs["overlay_ethnicity_totals"] = go.Figure()

#     # ────────── Mental health (if available) ──────────
#     avail_cfq = [c for c in CFQ_VARS if c in baseline.columns]
#     if avail_cfq:
#         cfq_any   = baseline[avail_cfq].notna().any(axis=1)
#         total_yes = baseline[avail_cfq].fillna(0).sum(axis=1)

#         mh_long = (baseline.loc[cfq_any, ["record_id","site"] + avail_cfq]
#                    .melt(id_vars=["record_id","site"], value_name="val")
#                    .query("val == 1")
#                    .assign(Diagnosis=lambda d: d["variable"].map(CFQ_LABELS)))

#         mh_counts = (mh_long.groupby(["site","Diagnosis"])["record_id"]
#                      .nunique().reset_index(name="Count"))

#         # Bar (positives only)
#         if not mh_counts.empty:
#             figs["mh_bar"] = px.bar(
#                 mh_counts, x="Diagnosis", y="Count", color="site",
#                 category_orders={"site": SITE_ORDER},
#                 color_discrete_map=SITE_COLOURS,
#                 title="Child mental health & neurodevelopmental diagnoses (participant report)"
#             )
#         else:
#             figs["mh_bar"] = go.Figure()

#         # Heatmap of counts by site
#         heat = mh_counts.pivot(index="Diagnosis", columns="site", values="Count").reindex(columns=SITE_ORDER, fill_value=0)
#         if not heat.empty:
#             figs["mh_heatmap"] = px.imshow(
#                 heat, text_auto=True, aspect="auto", color_continuous_scale="Reds",
#                 title="Counts of diagnoses by site"
#             )
#         else:
#             figs["mh_heatmap"] = go.Figure()

#         # Add "No diagnosis" row for display (derived from cfq_any & total_yes==0)
#         no_dx_mask   = cfq_any & (total_yes == 0)
#         no_dx_counts = (baseline.loc[no_dx_mask].groupby("site")["record_id"]
#                         .nunique().reindex(SITE_ORDER, fill_value=0))
#         if not heat.empty:
#             heat_all = pd.concat([heat, pd.DataFrame([no_dx_counts], index=["No diagnosis"])], axis=0)
#             figs["mh_heatmap_with_nodx"] = px.imshow(
#                 heat_all, text_auto=True, aspect="auto", color_continuous_scale="Reds",
#                 title="Counts of diagnoses by site (incl. 'No diagnosis')"
#             )
#         else:
#             figs["mh_heatmap_with_nodx"] = go.Figure()

#         # Correlation (phi) across CFQ vars
#         cfq_data = baseline[["record_id","site"] + avail_cfq].dropna(how="all", subset=avail_cfq)
#         if not cfq_data.empty:
#             cfq_bin = cfq_data[avail_cfq].fillna(0).astype(int)
#             corr = cfq_bin.corr(method="pearson")
#             figs["mh_corr"] = px.imshow(
#                 corr, text_auto=True, zmin=-1, zmax=1, color_continuous_scale="RdBu",
#                 title="Correlation between diagnoses"
#             )
#             # Co-occurrence (counts)
#             co = cfq_bin.T.dot(cfq_bin)
#             co = co.rename(index=CFQ_LABELS, columns=CFQ_LABELS)
#             figs["mh_cooccurrence"] = px.imshow(
#                 co, text_auto=True, aspect="auto", color_continuous_scale="Reds",
#                 title="Co-occurrence of diagnoses (counts)"
#             )
#         else:
#             figs["mh_corr"] = go.Figure()
#             figs["mh_cooccurrence"] = go.Figure()
#     else:
#         figs["mh_bar"] = go.Figure()
#         figs["mh_heatmap"] = go.Figure()
#         figs["mh_heatmap_with_nodx"] = go.Figure()
#         figs["mh_corr"] = go.Figure()
#         figs["mh_cooccurrence"] = go.Figure()

#     # ────────── Tables to return ──────────
#     tables: Dict[str, pd.DataFrame] = {
#         "baseline": baseline,
#         "counts": counts.reset_index(names="site"),
#         "na_counts": na_counts.reset_index(names="site"),
#         "age_block_counts": age_block_counts,
#         "eth_long": eth_long,
#         "eth_counts_panel": eth_counts_panel,
#         "eth_wnw_counts": eth_wnw_counts,
#         "income_counts": (
#             inc_non_na.groupby(["site","income_lbl"])["record_id"]
#             .nunique().reset_index(name="Count") if not inc_non_na.empty else pd.DataFrame()
#         ),
#         "na_counts_long": na_counts_long,
#         "timeline": timeline,
#         "targets_age_group": targets_age_group,
#         "obs_sex_age_blocks": obs_sex_age_blocks,
#         "obs_eth_age_blocks": obs_eth_age_blocks,
#         "obs_eth_tot": obs_eth_tot,
#         "targets_tot_eth": targets_tot_eth,
#     }

#     return {"tables": tables, "figures": figs}
