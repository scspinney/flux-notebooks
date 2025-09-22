# src/flux_notebooks/redcap/summarize_redcap.py
from __future__ import annotations
import re, glob
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import numpy as np
import pandas as pd

import plotly.express as px
import plotly.graph_objects as go

MIN_T1_DATE = pd.Timestamp("2023-01-01")
MRI_INSTRUMENT = "mri"  # repeat instrument name (lower-case)

SITE_ORDER   = ["Calgary", "Montreal", "Toronto"]
SITE_COLOURS = {"Montreal": "#1f77b4", "Calgary": "#ff0e0e", "Toronto": "#2ca02c"}

MEASURE_ORDER   = ["Target", "Observed"]
MEASURE_COLOURS = {"Target": "#f58518", "Observed": "#4c78a8"}

AGE_BLOCK_ORDER = ["0-2", "2-5", "6-9", "10-12", "13-15", "16-18"]
AGE_BIN_ORDER   = ["<5wks"] + [f"{i}-{i+1}" for i in range(0, 18)] + ["18"]

ETHNICITY_ORDER_TARGET = ["White", "Asian", "Black", "Indigenous", "Middle East", "Latin American", "Other"]

TARGET_TOTALS = {
    "Calgary":  {"Ethnicity": {"White":153,"Asian":63,"Black":11,"Indigenous":8,"Middle East":8,"Latin American":5,"Other":16}},
    "Toronto":  {"Ethnicity": {"White":124,"Asian":87,"Black":24,"Indigenous":3,"Middle East":11,"Latin American":8,"Other":8}},
    "Montreal": {"Ethnicity": {"White":171,"Asian":29,"Black":26,"Indigenous":3,"Middle East":21,"Latin American":11,"Other":3}},
}

ASIAN = {"East Asian","South Asian","Southeast Asian"}
INDIG = {"First Nations","Inuk/Inuit","Métis"}

sex_map = {1:"Male",2:"Female",3:"Intersex / Non-binary",777:"Unknown",888:"Prefer not to answer", np.nan:"NA"}
gender_map = {1:"Boy/Man",2:"Girl/Woman",3:"Non-binary",4:"Two-spirit",5:"Another",
              6:"Questioning",777:"Unknown",888:"Prefer not to answer", np.nan:"NA"}
income_map = {1:"Under $10k",2:"$10-19k",3:"$20-39k",4:"$40-59k",5:"$60-79k",
              6:"$80-99k",7:"$100-124k",8:"$125-149k",9:"$150-199k",
              10:"$200-299k",11:"$300-399k",12:"$400k+",777:"Unknown",888:"Prefer not to say"}

def derive_site(p: Path) -> str:
    s = p.stem.lower()
    if "montreal" in s: return "Montreal"
    if "calgary"  in s: return "Calgary"
    if "toronto"  in s: return "Toronto"
    raise ValueError(f"Cannot infer site from filename: {p.name}")

def load_csv(p: Path) -> pd.DataFrame:
    d = pd.read_csv(p, low_memory=False)
    d["site"] = derive_site(p)
    return d

def pick_first(df: pd.DataFrame, names: List[str], *, required=False) -> Optional[str]:
    for n in names:
        if n in df.columns:
            return n
    if required:
        raise ValueError(f"None of {names} found in dataframe columns.")
    return None

_bracket_median = {
     1:   5_000,  2:  15_000,  3:  30_000,  4:  50_000,
     5:  70_000,  6:  90_000,  7: 112_500,  8: 137_500,
     9: 175_000, 10: 250_000, 11: 350_000, 12: 450_000
}
SPECIAL_INCOME = {777, 888}
def closest_code_from_dollars(amount: float) -> int:
    return int(min(_bracket_median, key=lambda c: abs(_bracket_median[c] - amount)))

def _as_int_or_nan(x):
    try:
        return int(x)
    except Exception:
        return np.nan

def merge_income_row(row: pd.Series):
    cg = _as_int_or_nan(row.get("demo_cg_income"))
    pt = _as_int_or_nan(row.get("demo_cg_prtnr_income"))
    if cg in SPECIAL_INCOME: return cg
    if pt in SPECIAL_INCOME: return pt
    if pd.isna(cg) and pd.isna(pt): return np.nan
    if pd.isna(pt): return cg
    if pd.isna(cg): return pt
    total = _bracket_median[int(cg)] + _bracket_median[int(pt)]
    return closest_code_from_dollars(total)

def best_baseline_rows(df: pd.DataFrame, key_vars: List[str]) -> pd.DataFrame:
    t1 = df[df["redcap_event_name"] == "t1_arm_1"].copy()
    t1["_score"] = t1[key_vars].notna().sum(axis=1)
    t1 = t1.sort_values(["record_id", "_score"], ascending=[True, False])
    best = t1.drop_duplicates(subset="record_id").drop(columns="_score")
    return best.reset_index(drop=True)

def to_age_block(a: float) -> Optional[str]:
    if pd.isna(a): return None
    if a <= 2:   return "0-2"
    if a <= 5:   return "2-5"
    if a <= 9:   return "6-9"
    if a <= 12:  return "10-12"
    if a <= 15:  return "13-15"
    if a <= 18:  return "16-18"
    return None

def bin_label_to_block(lbl: str) -> Optional[str]:
    if lbl is None: return None
    if lbl == "<5wks": return None
    if lbl == "18": return "16-18"
    m = re.match(r"^(\d+)-(\d+)$", str(lbl))
    if not m: return None
    k = int(m.group(1))
    if k < 2:   return "0-2"
    if k < 6:   return "2-5"
    if k < 10:  return "6-9"
    if k < 13:  return "10-12"
    if k < 16:  return "13-15"
    return "16-18"

def collapse_eth(lbl: str) -> Optional[str]:
    if lbl in ASIAN: return "Asian"
    if lbl in INDIG: return "Indigenous"
    if lbl == "Middle Eastern": return "Middle East"
    if lbl in {"Black","Middle East","Latin American","Other","White"}: return lbl
    return None

def _find_age_file(root: Path, stem: str) -> Optional[Path]:
    for p in root.glob(f"*{stem.lower()}*age_by_group*.csv"):
        return p
    return None

def _targets_age_group(root: Path) -> pd.DataFrame:
    rows = []
    for stem in ("calgary", "montreal", "toronto"):
        p = _find_age_file(root, stem)
        if p is None:
            continue
        site = derive_site(p)
        t = pd.read_csv(p, comment="#").rename(columns={"5 wks pre": "<5wks"})
        keep_cols = ["Group"] + AGE_BIN_ORDER + ["Total"]
        cols = [c for c in keep_cols if c in t.columns]
        if "Group" not in cols:
            continue
        value_cols = [c for c in AGE_BIN_ORDER if c in cols]
        long = t.melt(id_vars=["Group"], value_vars=value_cols,
                      var_name="age_bin_label", value_name="Target_N")
        long["site"] = site
        long["Group"] = long["Group"].replace({"Middle Eastern": "Middle East"})
        rows.append(long[["site","Group","age_bin_label","Target_N"]])
    if not rows:
        return pd.DataFrame(columns=["site","Group","age_bin_label","Target_N"])
    out = pd.concat(rows, ignore_index=True)
    out["Target_N"] = pd.to_numeric(out["Target_N"], errors="coerce").fillna(0.0)
    out["age_bin_label"] = pd.Categorical(out["age_bin_label"], categories=AGE_BIN_ORDER, ordered=True)
    return out

def _px_bar(df, x, y, color=None, facet_row=None, facet_col=None, category_orders=None,
            barmode="group", title=None, color_discrete_map=None, labels=None):
    fig = px.bar(
        df, x=x, y=y, color=color,
        facet_row=facet_row, facet_col=facet_col,
        barmode=barmode, category_orders=(category_orders or {}),
        color_discrete_map=(color_discrete_map or {}),
        labels=(labels or {}),
    )
    fig.update_layout(
        title=title,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        bargap=0.15,
        template="plotly_white",
    )
    fig.update_xaxes(tickangle=0)
    return fig

def summarize_redcap(dataset_root: Path) -> Dict[str, object]:
    """
    Build all REDCap figures for the Dash page.
    Returns: {"figures": {...}, "counts": DataFrame, "baseline": DataFrame, ...}
    """
    root = Path(dataset_root)
    # Try obvious CSVs in the root; if not, accept any of *montreal*.csv etc.
    candidates = []
    for pat in ("*montreal*.csv","*calgary*.csv","*toronto*.csv"):
        candidates += [Path(p) for p in glob.glob(str(root / pat))]
    if not candidates:
        # Also try current working directory (for dev runs)
        for pat in ("*montreal*.csv","*calgary*.csv","*toronto*.csv"):
            candidates += [Path(p) for p in glob.glob(pat)]
    if not candidates:
        raise RuntimeError(f"No site CSVs found under {root} (or cwd).")

    df_main = pd.concat([load_csv(p) for p in candidates], ignore_index=True)

    # Non-repeat instrument rows
    non_repeat = df_main[df_main["redcap_repeat_instrument"].isna()].copy()

    # Column resolution
    SEX_COL    = pick_first(non_repeat, ["sex","demo_sex"], required=False) or "sex"
    GENDER_COL = pick_first(non_repeat, ["gender","demo_gender","gender_oth"], required=False) or "gender"

    # Income merge (if dual fields present)
    if {"demo_cg_income", "demo_cg_prtnr_income"} & set(non_repeat.columns):
        non_repeat["demo_cg_income"] = non_repeat.apply(merge_income_row, axis=1)
    elif "demo_cg_prtnr_income" in non_repeat.columns:
        non_repeat["demo_cg_income"] = non_repeat["demo_cg_prtnr_income"].apply(_as_int_or_nan)
    else:
        non_repeat["demo_cg_income"] = non_repeat.get("demo_cg_income", np.nan).apply(_as_int_or_nan)

    # Ethnicity checkbox columns
    ETH_COLS = [c for c in non_repeat.columns if re.match(r"(demo_)?ethnicity___\d+", c)]
    key_vars = ["youth_age_y", "youth_age_m", SEX_COL, GENDER_COL, "demo_cg_income"] + ETH_COLS
    baseline = best_baseline_rows(non_repeat, key_vars)

    # Derived age & labels
    def _age_years(row):
        y, m = row.get("youth_age_y"), row.get("youth_age_m")
        if pd.isna(y) and pd.isna(m): return np.nan
        return (0 if pd.isna(y) else y) + (0 if pd.isna(m) else m) / 12
    baseline["age_years"]  = baseline.apply(_age_years, axis=1)
    baseline["sex_lbl"]    = baseline[SEX_COL].map(sex_map) if SEX_COL in baseline else np.nan
    baseline["gender_lbl"] = baseline[GENDER_COL].map(gender_map) if GENDER_COL in baseline else np.nan
    baseline["income_lbl"] = baseline["demo_cg_income"].map(income_map) if "demo_cg_income" in baseline else np.nan

    # Ethnicity long and white-only logic
    if ETH_COLS:
        baseline[ETH_COLS] = baseline[ETH_COLS].fillna(0)
        eth_lookup = {f"{p}{i}": lbl
                      for p in ("demo_ethnicity___","demo_cg_ethnicity___")
                      for i,lbl in {
                          1:"Black",2:"East Asian",3:"First Nations",4:"Inuk/Inuit",5:"Métis",
                          6:"Latin American",7:"Middle Eastern",8:"South Asian",9:"Southeast Asian",
                          10:"White",11:"Other",888:"Prefer not to say"}.items()}
        eth_long = (baseline[["record_id","site"]+ETH_COLS]
                    .melt(id_vars=["record_id","site"], value_name="val")
                    .query("val == 1")
                    .assign(label=lambda d: d["variable"].map(eth_lookup)))
    else:
        eth_long = pd.DataFrame(columns=["record_id","site","variable","val","label"])

    # White-only vs non-white wide helper
    eth_wide = pd.DataFrame()
    if not eth_long.empty:
        tmp = (eth_long.groupby(["site","record_id"])["label"]
               .apply(lambda s: sorted(set(s.dropna()))).reset_index(name="labels"))
        tmp["is_white_only"] = tmp["labels"].apply(lambda L: ("White" in set(L)) and (len(set(L))==1))
        tmp["has_nonwhite"]  = tmp["labels"].apply(lambda L: any(l!="White" for l in set(L)))
        eth_wide = tmp[["site","record_id","is_white_only","has_nonwhite"]].copy()
        eth_wide["White"] = eth_wide["is_white_only"].map({True:"White", False:np.nan})
        eth_wide["Non-white"] = eth_wide["has_nonwhite"].map({True:"Non-white", False:np.nan})
        eth_wide = eth_wide[["site","record_id","White","Non-white"]]

    # MRI baseline rows & timeline
    mri_base = df_main.loc[
        (df_main["redcap_event_name"] == "t1_arm_1") &
        (df_main["redcap_repeat_instrument"].fillna("").str.strip().str.lower() == MRI_INSTRUMENT)
    ].copy()
    if "mri_date" in mri_base.columns:
        mri_base["mri_date"] = pd.to_datetime(mri_base["mri_date"], errors="coerce").dt.normalize()
    else:
        mri_base["mri_date"] = pd.NaT
    mri_base = (mri_base.dropna(subset=["mri_date"])
                        .loc[mri_base["mri_date"] >= MIN_T1_DATE]
                        .sort_values("mri_complete", ascending=False)
                        .drop_duplicates(subset=["record_id","mri_date"]))
    sched = (mri_base.groupby(["site","mri_date"])["record_id"].nunique()
                    .groupby(level=0).cumsum().rename("cum").reset_index().assign(status="Scheduled"))
    comp  = (mri_base[mri_base.get("mri_complete", 0) == 2].groupby(["site","mri_date"])["record_id"].nunique()
                    .groupby(level=0).cumsum().rename("cum").reset_index().assign(status="Completed"))
    timeline = pd.concat([sched, comp], ignore_index=True) if not mri_base.empty else pd.DataFrame()

    # Counts / NA counts
    site_totals = baseline.groupby("site")["record_id"].nunique()
    def _count_non_na(column: str) -> pd.Series:
        return (baseline[baseline[column].notna()].groupby("site")["record_id"].nunique())
    counts = pd.DataFrame({"Total available counts": site_totals})
    for col in ["age_years","sex_lbl","gender_lbl","income_lbl"]:
        if col in baseline:
            counts[f"{col.split('_')[0].capitalize()} non-NA"] = _count_non_na(col)
    if not eth_long.empty:
        eth_non_na = eth_long.groupby("site")["record_id"].nunique().rename("Ethnicity non-NA")
        counts = counts.join(eth_non_na, how="left")
    counts = counts.fillna(0).astype(int)
    na_counts = pd.DataFrame({"Total available counts": site_totals})
    na_counts["Age NA"]    = site_totals - counts.get("Age non-NA", 0)
    na_counts["Sex NA"]    = site_totals - counts.get("Sex non-NA", 0)
    na_counts["Gender NA"] = site_totals - counts.get("Gender non-NA", 0)
    na_counts["Income NA"] = site_totals - counts.get("Income non-NA", 0)
    if "Ethnicity non-NA" in counts:
        na_counts["Ethnicity NA"] = site_totals - counts["Ethnicity non-NA"]
    na_counts = na_counts.fillna(0).astype(int)

    # =============== FIGURES =================
    figs: Dict[str, go.Figure] = {}

    # ── Age groups by site (baseline) — categorical blocks, not dates ───────────
    if "age_years" in baseline:
        age_block_counts = (
            baseline.assign(age_block=lambda d: d["age_years"].apply(to_age_block))
                    .dropna(subset=["age_block"])
                    .groupby(["site","age_block"])["record_id"]
                    .nunique()
                    .reset_index(name="Count")
        )

        if not age_block_counts.empty:
            # Force categorical ordering so Plotly won't guess "date"s
            AGE_BLOCKS = ["0-2","2-5","6-9","10-12","13-15","16-18"]
            age_block_counts["age_block"] = pd.Categorical(
                age_block_counts["age_block"], categories=AGE_BLOCKS, ordered=True
            ).astype(str)

            fig_age = px.bar(
                age_block_counts,
                x="age_block",
                y="Count",
                color="site",
                barmode="group",
                category_orders={"age_block": AGE_BLOCKS, "site": SITE_ORDER},
                color_discrete_map=SITE_COLOURS,
                labels={"age_block": "Age group", "Count": "Participants"},
                title="Age groups by site (baseline)",
            )
            # Belt-and-suspenders: lock axis type to category
            fig_age.update_xaxes(type="category", tickangle=0)
            fig_age.update_layout(template="plotly_white", margin=dict(l=10,r=10,t=50,b=10))

            figs["age"] = fig_age


    # Sex
    if "sex_lbl" in baseline:
        order_sex = ["Male","Female","Intersex / Non-binary","Unknown","Prefer not to answer","NA"]
        sex_df = baseline.dropna(subset=["sex_lbl"])
        if not sex_df.empty:
            sex_counts = (sex_df.groupby(["site","sex_lbl"])["record_id"].nunique().reset_index(name="Count"))
            figs["sex"] = _px_bar(
                sex_counts, x="sex_lbl", y="Count", color="site",
                category_orders={"sex_lbl": order_sex, "site": SITE_ORDER},
                title="Sex assigned at birth (baseline)",
                color_discrete_map=SITE_COLOURS,
                labels={"sex_lbl":"Sex","Count":"Participants"}
            )

    # Gender
    if "gender_lbl" in baseline:
        order_g = ["Boy/Man","Girl/Woman","Non-binary","Two-spirit","Another","Questioning","Unknown","Prefer not to answer","NA"]
        g_df = baseline.dropna(subset=["gender_lbl"])
        if not g_df.empty:
            g_counts = (g_df.groupby(["site","gender_lbl"])["record_id"].nunique().reset_index(name="Count"))
            figs["gender"] = _px_bar(
                g_counts, x="gender_lbl", y="Count", color="site",
                category_orders={"gender_lbl": order_g, "site": SITE_ORDER},
                title="Current gender identity (baseline)",
                color_discrete_map=SITE_COLOURS,
                labels={"gender_lbl":"Gender","Count":"Participants"}
            )

    # Ethnicity full
    if not eth_long.empty:
        order_eth_full = eth_long["label"].value_counts().index.tolist()
        eth_counts = (eth_long.groupby(["site","label"])["record_id"].nunique().reset_index(name="Count"))
        figs["ethnicity_full"] = _px_bar(
            eth_counts, x="label", y="Count", color="site",
            category_orders={"label": order_eth_full, "site": SITE_ORDER},
            title="Ethnicity (baseline)",
            color_discrete_map=SITE_COLOURS,
            labels={"label":"Ethnicity","Count":"Participants"}
        )

    # Ethnicity White/Non-white
    if not eth_wide.empty:
        eth_wide_long = eth_wide.melt(id_vars=["site","record_id"], value_vars=["White","Non-white"],
                                      var_name="Ethnicity", value_name="Label")
        eth_wide_long = eth_wide_long[eth_wide_long["Label"].notna() & (eth_wide_long["Label"] != "")]
        eth_counts_panel = (eth_wide_long.groupby(["site","Ethnicity"])["record_id"]
                            .nunique().reset_index(name="Count"))
        figs["ethnicity_white_nonwhite"] = _px_bar(
            eth_counts_panel, x="Ethnicity", y="Count", color="site",
            category_orders={"Ethnicity": ["White","Non-white"], "site": SITE_ORDER},
            title="Ethnicity (White/Non-white) by site",
            color_discrete_map=SITE_COLOURS,
            labels={"Count":"Participants"}
        )

    # Income
    if "income_lbl" in baseline and not baseline["income_lbl"].dropna().empty:
        order_inc = [income_map[i] for i in range(1, 13)] + [income_map[777], income_map[888]]
        inc_df = baseline.dropna(subset=["income_lbl"])
        inc_counts = (inc_df.groupby(["site","income_lbl"])["record_id"].nunique().reset_index(name="Count"))
        figs["income"] = _px_bar(
            inc_counts, x="income_lbl", y="Count", color="site",
            category_orders={"income_lbl": order_inc, "site": SITE_ORDER},
            title="Household income (baseline)",
            color_discrete_map=SITE_COLOURS,
            labels={"income_lbl":"Income","Count":"Participants"}
        )

    # MRI timeline
    if not timeline.empty:
        timeline = timeline.copy()
        timeline["mri_date"] = pd.to_datetime(timeline["mri_date"])
        fig_t = px.line(
            timeline, x="mri_date", y="cum", color="site", line_dash="status",
            category_orders={"site": SITE_ORDER, "status": ["Scheduled","Completed"]},
            color_discrete_map=SITE_COLOURS,
            labels={"mri_date":"Date","cum":"Cumulative T1 MRIs"},
            title="Baseline MRI visits by site"
        )
        fig_t.update_layout(template="plotly_white", margin=dict(l=10,r=10,t=50,b=10))
        figs["mri_timeline"] = fig_t

    # Missing counts
    if not na_counts.empty:
        na_long = (na_counts.reset_index()
                   .rename(columns={"index":"site"})
                   .melt(id_vars="site", var_name="Metric", value_name="Count"))
        metric_order = ["Total available counts","Age NA","Sex NA","Gender NA","Income NA","Ethnicity NA"]
        na_long["Metric"] = pd.Categorical(na_long["Metric"], categories=metric_order, ordered=True)
        figs["missing_counts"] = _px_bar(
            na_long, x="Metric", y="Count", color="site",
            category_orders={"Metric": metric_order, "site": SITE_ORDER},
            title="Missing counts per panel",
            color_discrete_map=SITE_COLOURS,
            labels={"Metric":"Panel","Count":"Count"}
        )

    # ======== Targets & overlays
    targets_root = root  # put the *age_by_group.csv files next to site CSVs
    targets_age_group = _targets_age_group(targets_root)

    # Observed Sex×Age blocks (Male/Female only)
    obs_sex_age_blocks = pd.DataFrame()
    if "sex_lbl" in baseline:
        obs_sex_age_blocks = (
            baseline.dropna(subset=["sex_lbl","age_years"])
                    .assign(age_block=lambda d: d["age_years"].apply(to_age_block))
                    .dropna(subset=["age_block"])
                    .query("sex_lbl in ['Male','Female']")
                    .groupby(["site","sex_lbl","age_block"])["record_id"].nunique()
                    .reset_index(name="Observed_N")
        )

    # Observed Ethnicity×Age blocks (with collapse + white-only)
    obs_eth_age_blocks = pd.DataFrame()
    if not eth_long.empty:
        by_rec = (eth_long.groupby(["site","record_id"])["label"]
                  .apply(lambda s: sorted(set(s.dropna()))).reset_index(name="labels"))
        white_ids = set(by_rec.loc[by_rec["labels"].apply(lambda L: ("White" in set(L)) and (len(set(L))==1)),
                                   "record_id"])
        white_only_df = (baseline.loc[baseline["record_id"].isin(white_ids),
                                      ["record_id","site","age_years"]]
                         .assign(Ethnicity="White",
                                 age_block=lambda d: d["age_years"].apply(to_age_block)))
        nonwhite = by_rec.loc[by_rec["labels"].apply(lambda L: any(l!="White" for l in set(L)))].copy()
        nonwhite = (nonwhite.assign(EthnicityList=nonwhite["labels"].apply(lambda L: [l for l in L if l!="White"]))
                            .explode("EthnicityList")
                            .rename(columns={"EthnicityList":"Ethnicity"})
                            .drop(columns="labels"))
        nonwhite["Ethnicity"] = nonwhite["Ethnicity"].map(collapse_eth)
        nonwhite = nonwhite.dropna(subset=["Ethnicity"])
        nonwhite = (nonwhite.merge(baseline[["record_id","age_years"]], on="record_id", how="left")
                            .assign(age_block=lambda d: d["age_years"].apply(to_age_block)))
        parts = []
        if not white_only_df.empty:
            parts.append(white_only_df[["site","Ethnicity","age_block","record_id"]])
        if not nonwhite.empty:
            parts.append(nonwhite[["site","Ethnicity","age_block","record_id"]])
        if parts:
            obs_eth_age_blocks = (pd.concat(parts, ignore_index=True)
                                    .dropna(subset=["age_block"])
                                    .groupby(["site","Ethnicity","age_block"])["record_id"]
                                    .nunique().reset_index(name="Observed_N"))

    # ── Overlay: Age × Sex (force categorical x across all facets) ──────────────
    if (not targets_age_group.empty) and (not obs_sex_age_blocks.empty):
        targ_sex = targets_age_group[targets_age_group["Group"].isin(["Male","Female"])].copy()
        targ_sex["age_block"] = targ_sex["age_bin_label"].map(bin_label_to_block)
        targ_sex = (targ_sex.dropna(subset=["age_block"])
                            .groupby(["site","Group","age_block"])["Target_N"]
                            .sum().reset_index()
                            .rename(columns={"Group":"sex_lbl"}))

        sx_obs = obs_sex_age_blocks.rename(columns={"Observed_N":"N"}).assign(Measure="Observed")
        sx_tgt = targ_sex.rename(columns={"Target_N":"N"}).assign(Measure="Target")
        sx_long = pd.concat([sx_tgt, sx_obs], ignore_index=True)

        AGE_BLOCKS = ["0-2","2-5","6-9","10-12","13-15","16-18"]
        sx_long["age_block"] = pd.Categorical(sx_long["age_block"],
                                            categories=AGE_BLOCKS, ordered=True).astype(str)

        fig = px.bar(
            sx_long,
            x="age_block", y="N", color="Measure",
            facet_row="sex_lbl", facet_col="site",
            barmode="group",
            category_orders={"age_block": AGE_BLOCKS, "site": SITE_ORDER, "Measure": MEASURE_ORDER},
            color_discrete_map=MEASURE_COLOURS,
            labels={"age_block":"Age group","N":"Participants"},
            title="Observed vs Target by Age × Sex, per site",
        )
        # Force *all* x-axes in the faceted fig to categorical
        fig.for_each_xaxis(lambda ax: ax.update(type="category", tickangle=0))
        fig.update_layout(template="plotly_white", margin=dict(l=10,r=10,t=50,b=10))
        figs["overlay_age_sex"] = fig


    # ── Overlay: Age × Ethnicity (force categorical x across all facets) ────────
    if (not targets_age_group.empty) and (not obs_eth_age_blocks.empty):
        targ_eth = targets_age_group[targets_age_group["Group"].isin(ETHNICITY_ORDER_TARGET)].copy()
        targ_eth["age_block"] = targ_eth["age_bin_label"].map(bin_label_to_block)
        targ_eth = (targ_eth.dropna(subset=["age_block"])
                            .groupby(["site","Group","age_block"])["Target_N"].sum().reset_index()
                            .rename(columns={"Group":"Ethnicity"}))

        et_obs = obs_eth_age_blocks.rename(columns={"Observed_N":"N"}).assign(Measure="Observed")
        et_tgt = targ_eth.rename(columns={"Target_N":"N"}).assign(Measure="Target")
        et_long = pd.concat([et_tgt, et_obs], ignore_index=True)

        AGE_BLOCKS = ["0-2","2-5","6-9","10-12","13-15","16-18"]
        et_long["age_block"] = pd.Categorical(et_long["age_block"],
                                            categories=AGE_BLOCKS, ordered=True).astype(str)
        et_long["Ethnicity"] = pd.Categorical(et_long["Ethnicity"],
                                            categories=ETHNICITY_ORDER_TARGET, ordered=True).astype(str)

        fig = px.bar(
            et_long,
            x="age_block", y="N", color="Measure",
            facet_row="Ethnicity", facet_col="site",
            barmode="group",
            category_orders={
                "age_block": AGE_BLOCKS,
                "Ethnicity": ETHNICITY_ORDER_TARGET,
                "site": SITE_ORDER,
                "Measure": MEASURE_ORDER,
            },
            color_discrete_map=MEASURE_COLOURS,
            labels={"age_block":"Age group","N":"Participants"},
            title="Observed vs Target by Age × Ethnicity, per site",
        )
        fig.for_each_xaxis(lambda ax: ax.update(type="category", tickangle=0))
        fig.update_layout(template="plotly_white", margin=dict(l=10,r=10,t=50,b=10))
        figs["overlay_age_ethnicity"] = fig


    # Overlay: Ethnicity totals (Observed vs Target)
    obs_eth_tot = pd.DataFrame()
    if not eth_long.empty:
        by_rec2 = eth_long.copy()
        by_rec2["Ethnicity"] = by_rec2["label"].map(lambda x: collapse_eth(x))
        by_rec2 = by_rec2.dropna(subset=["Ethnicity"])
        # White-only totals: include White only if the ONLY label
        # (reuse white-only from previous block if available)
        if 'white_only_df' in locals() and not white_only_df.empty:
            white_tot = white_only_df[["site","record_id"]].assign(Ethnicity="White")
        else:
            white_tot = pd.DataFrame(columns=["site","record_id","Ethnicity"])
        nonwhite_tot = by_rec2[by_rec2["Ethnicity"]!="White"][["site","record_id","Ethnicity"]].drop_duplicates()
        obs_all = pd.concat([white_tot, nonwhite_tot], ignore_index=True)
        obs_eth_tot = (obs_all.groupby(["site","Ethnicity"])["record_id"]
                       .nunique().reset_index(name="Observed_N"))
    rows=[]
    for site, payload in TARGET_TOTALS.items():
        for eth, n in payload["Ethnicity"].items():
            rows.append({"site":site, "Ethnicity":eth, "Target_N": int(n)})
    targets_tot_eth = pd.DataFrame(rows)
    if not obs_eth_tot.empty and not targets_tot_eth.empty:
        compare_df = (targets_tot_eth.merge(obs_eth_tot, on=["site","Ethnicity"], how="left")
                                     .fillna({"Observed_N":0}).astype({"Observed_N":int}))
        cmp_long = pd.concat([
            compare_df.rename(columns={"Target_N":"N"})[["site","Ethnicity","N"]].assign(Measure="Target"),
            compare_df.rename(columns={"Observed_N":"N"})[["site","Ethnicity","N"]].assign(Measure="Observed")
        ], ignore_index=True)
        cmp_long["Ethnicity"] = pd.Categorical(cmp_long["Ethnicity"], categories=ETHNICITY_ORDER_TARGET, ordered=True)
        figs["overlay_ethnicity_totals"] = _px_bar(
            cmp_long, x="Ethnicity", y="N", color="Measure",
            facet_col="site",
            category_orders={"Ethnicity": ETHNICITY_ORDER_TARGET, "site": SITE_ORDER, "Measure": MEASURE_ORDER},
            barmode="group",
            title="Observed vs Target recruitment by Ethnicity and Site",
            color_discrete_map=MEASURE_COLOURS,
            labels={"N":"Participants"}
        )

    # ======== CFQ mental health panels ========
    cfq_vars = [
        "cfq_diag_asd_part","cfq_diag_id_part","cfq_adhd_part","cfq_fasd_part",
        "cfq_ld_part","cfq_lcd_part","cfq_md_part","cfq_diag_other_part",
        "cfq_ment_ad_part","cfq_ment_dd_part","cfq_ment_bd_part","cfq_ment_ocd_part",
        "cfq_ment_ts_part","cfq_ment_psyep_part","cfq_ment_schizo_part",
        "cfq_ment_sa_part","cfq_ment_epilepsy_part","cfq_ment_other_part"
    ]
    cfq_labels = {
        "cfq_diag_asd_part": "Autism Spectrum Disorder",
        "cfq_diag_id_part": "Cognitive Impair/IDD",
        "cfq_adhd_part": "ADHD",
        "cfq_fasd_part": "FASD",
        "cfq_ld_part": "Learning Disability",
        "cfq_lcd_part": "Language Disorder",
        "cfq_md_part": "Motor Disorder",
        "cfq_diag_other_part": "Other Neurodev.",
        "cfq_ment_ad_part": "Anxiety Disorder",
        "cfq_ment_dd_part": "Depressive Disorder",
        "cfq_ment_bd_part": "Bipolar Disorder",
        "cfq_ment_ocd_part": "OCD",
        "cfq_ment_ts_part": "Tourette’s",
        "cfq_ment_psyep_part": "Psychosis",
        "cfq_ment_schizo_part": "Schizophrenia",
        "cfq_ment_sa_part": "Substance Abuse",
        "cfq_ment_epilepsy_part": "Epilepsy",
        "cfq_ment_other_part": "Other (MH)"
    }

    avail_cfq = [c for c in cfq_vars if c in baseline.columns]
    if avail_cfq:
        cfq_any   = baseline[avail_cfq].notna().any(axis=1)
        total_yes = baseline[avail_cfq].fillna(0).sum(axis=1)

        mh_long = (baseline.loc[cfq_any, ["record_id","site"] + avail_cfq]
                   .melt(id_vars=["record_id","site"], value_name="val")
                   .query("val == 1")
                   .assign(Diagnosis=lambda d: d["variable"].map(cfq_labels)))
        mh_counts = (mh_long.groupby(["site","Diagnosis"])["record_id"]
                     .nunique().reset_index(name="Count"))

        # Bar (positives only)
        if not mh_counts.empty:
            figs["mh_bar"] = _px_bar(
                mh_counts, x="Diagnosis", y="Count", color="site",
                category_orders={"site": SITE_ORDER},
                title="Child MH & neurodev diagnoses (participant report)",
                color_discrete_map=SITE_COLOURS,
                labels={"Count":"Participants"}
            ).update_xaxes(tickangle=35)

            # Heatmap (+ 'No diagnosis' row)
            no_dx_mask   = cfq_any & (total_yes == 0)
            no_dx_counts = (baseline.loc[no_dx_mask].groupby("site")["record_id"]
                            .nunique().reindex(SITE_COLOURS.keys(), fill_value=0))
            heat = mh_counts.pivot(index="Diagnosis", columns="site", values="Count").fillna(0)
            heat_all = pd.concat([heat, pd.DataFrame([no_dx_counts.reindex(heat.columns, fill_value=0)],
                                                     index=["No diagnosis"])], axis=0).fillna(0)
            z = heat_all.values
            figs["mh_heatmap_with_nodx"] = go.Figure(data=go.Heatmap(
                z=z, x=list(heat_all.columns), y=list(heat_all.index),
                zmin=0, colorscale="Reds", colorbar=dict(title="Count")
            ))
            figs["mh_heatmap_with_nodx"].update_layout(
                title="Counts of diagnoses by site (includes ‘No diagnosis’)",
                template="plotly_white", margin=dict(l=10,r=10,t=50,b=10)
            )

            # Correlation & Co-occurrence (phi ~ Pearson on binaries)
            cfq_data = baseline[["record_id","site"] + avail_cfq].copy().dropna(how="all", subset=avail_cfq)
            cfq_bin = cfq_data[avail_cfq].fillna(0).astype(int)
            # Corr
            corr = cfq_bin.corr(method="pearson").fillna(0)
            corr_named = corr.rename(index=cfq_labels, columns=cfq_labels)
            figs["mh_corr"] = go.Figure(data=go.Heatmap(
                z=corr_named.values,
                x=list(corr_named.columns),
                y=list(corr_named.index),
                zmin=-1, zmax=1, colorscale="RdBu", colorbar=dict(title="Phi")
            ))
            figs["mh_corr"].update_layout(title="Correlation between diagnoses",
                                          template="plotly_white",
                                          margin=dict(l=10,r=10,t=50,b=10))
            # Co-occurrence counts
            co = cfq_bin.T.dot(cfq_bin)
            co_named = co.rename(index=cfq_labels, columns=cfq_labels)
            figs["mh_cooccurrence"] = go.Figure(data=go.Heatmap(
                z=co_named.values, x=list(co_named.columns), y=list(co_named.index),
                colorscale="Reds", colorbar=dict(title="Count")
            ))
            figs["mh_cooccurrence"].update_layout(title="Co-occurrence of diagnoses (counts)",
                                                  template="plotly_white",
                                                  margin=dict(l=10,r=10,t=50,b=10))

    return {
        "figures": figs,
        "counts": counts,
        "counts_na": na_counts,
        "baseline": baseline,
    }
