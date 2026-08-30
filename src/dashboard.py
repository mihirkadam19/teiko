"""Streamlit dashboard for Bob's analysis (Parts 2-4).

Run with:

    streamlit run dashboard.py

All computation lives in the part modules - this file only wires the imported
functions to Streamlit widgets.
"""

import os
import sqlite3
import sys

# `streamlit run src/dashboard.py` puts src/ on sys.path, not the repo root, so
# add the repo root to make the `src.` package importable regardless of CWD.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

from src.helpers import (
    AverageBCell,
    BaselineSubset,
    FrequencyTable,
    ResponderComparison,
)
from src.paths import DB_PATH
from src.analysis.responder_stats import (
    ALPHA,
    N_TESTS,
    POPULATIONS,
    TIMEPOINTS,
    make_boxplot,
    run_significance_tests,
)
from src.analysis.subset_analysis import summarize_baseline_subset
from src.paths import DB_PATH

if not os.path.exists(DB_PATH):
    import load_data
    load_data.main()



pd.set_option("styler.render.max_elements", 500_000)  

# --------------------------------------------------------------------------
# Shared connection + cached query results
# --------------------------------------------------------------------------

@st.cache_resource
def get_connection():
    """One SQLite connection for the whole app (read-only usage)."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


conn = get_connection()


@st.cache_data
def frequency_table():
    return FrequencyTable().run(conn)


@st.cache_data
def responder_data():
    return ResponderComparison().run(conn)


@st.cache_data
def significance_table():
    return run_significance_tests(ResponderComparison().run(conn))


@st.cache_data
def baseline_subset():
    return BaselineSubset().run(conn)


@st.cache_data
def avg_bcell():
    return AverageBCell().value(conn)


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------

st.set_page_config(page_title="Bob's analysis", layout="wide")
st.title("Bob's analysis")

tab_freq, tab_responder, tab_baseline = st.tabs(
    ["Frequency Table (Part 2)", "Responder Analysis (Part 3)", "Baseline Subset (Part 4)"]
)

# ---- Part 2 -------------------------------------------------------------
with tab_freq:
    st.header("Relative frequency of each cell population, per sample")
    st.markdown(
        "For every sample, each of the 5 immune populations is expressed as a "
        "percentage of that sample's total cell count "
        "(`count / total_count * 100`). One row per (sample, population), so the "
        "5 rows of any one sample sum to ~100%."
    )
    freq = frequency_table()

    samples = ["(all)"] + sorted(freq["sample"].unique())
    choice = st.selectbox("Filter to one sample", samples)
    view = freq if choice == "(all)" else freq[freq["sample"] == choice]

    avg_pct = (
        freq.groupby("population")["percentage"]
        .mean()
        .round(2)
        .reindex(["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"])
        .reset_index(name="avg_percentage")
    )

    avg_lookup = avg_pct.set_index("population")["avg_percentage"]

    def color_vs_avg_vectorized(df):
        pop_avg = df["population"].map(avg_lookup)
        colors = pd.Series("", index=df.index)
        colors[df["percentage"] > pop_avg] = "color: green"
        colors[df["percentage"] <= pop_avg] = "color: red"
        styles = pd.DataFrame("", index=df.index, columns=df.columns)
        styles["percentage"] = colors
        return styles

    styled_view = view.style.apply(color_vs_avg_vectorized, axis=None)

    table_col, avg_col = st.columns([3, 1])
    with table_col:
        st.caption(f"{len(view):,} rows")
        st.dataframe(styled_view, width="stretch", hide_index=True)
    with avg_col:
        st.caption("Average % per cell type (all samples)")
        st.dataframe(avg_pct, width="stretch", hide_index=True)


# ---- Part 3 -------------------------------------------------------------
with tab_responder:
    st.header("Responders vs non-responders (melanoma, miraclib, PBMC)")
    st.markdown(
        "Does any cell population's relative frequency differ between patients "
        "whose disease responded to miraclib and those whose didn't? Restricted "
        "to PBMC samples from melanoma patients on miraclib."
    )

    df = responder_data()
    stats = significance_table()

    st.markdown(
        "The analysis is run separately at each of the three sampling "
        f"timepoints ({', '.join(f't={t}' for t in TIMEPOINTS)} days from "
        "treatment start), so each subject contributes at most one observation "
        "per test. Pick a timepoint below to inspect its distributions and test "
        "results; the Bonferroni column is corrected across **all** "
        f"{N_TESTS} tests ({len(POPULATIONS)} populations x {len(TIMEPOINTS)} "
        "timepoints)."
    )

    timepoint = st.radio(
        "Timepoint (days from treatment start)",
        TIMEPOINTS,
        horizontal=True,
        format_func=lambda t: f"t = {t}",
    )

    tp_df = df[df["time_from_treatment_start"] == timepoint]
    tp_stats = stats[stats["timepoint"] == timepoint]
    n_resp = tp_df.loc[tp_df["response"] == "yes", "sample"].nunique()
    n_non = tp_df.loc[tp_df["response"] == "no", "sample"].nunique()

    st.subheader(f"Distribution by response (t = {timepoint})")
    st.markdown(
        f"One box per population, split by response "
        f"(**{n_resp:,}** responder samples vs **{n_non:,}** non responder at "
        f"this timepoint). Each y axis is that population's own percentage scale "
        "(every sample is drawn as a point over the box.)"
    )
    st.plotly_chart(make_boxplot(tp_df, timepoint), width="stretch")

    st.subheader(f"Mann Whitney U test per population (t = {timepoint})")
    st.markdown(
        "Test comparing the two groups' percentage "
        "distributions (no normality assumption). Columns: `statistic` = U, "
        "`p_value` = raw significance, `significant` = `p_value < "
        f"{ALPHA}`, `p_value_bonferroni` = p x {N_TESTS} "
        f"({len(POPULATIONS)} populations x {len(TIMEPOINTS)} timepoints, "
        "a conservative guard against false positives from multiple testing)."
    )
    st.dataframe(
        tp_stats.drop(columns="timepoint"), width="stretch", hide_index=True
    )

    sig = tp_stats.loc[tp_stats["significant"], "population"].tolist()
    sig_bonf = tp_stats.loc[
        tp_stats["p_value_bonferroni"] < ALPHA, "population"
    ].tolist()
    if sig:
        st.markdown(
            f"t = {timepoint} significant at raw p < {ALPHA}: "
            f"{','.join(sig)}.\n\n"
            + (
                f"Survives Bonferroni correction: {', '.join(sig_bonf)}."
                if sig_bonf
                else "None survive Bonferroni correction, so treat this as "
                "suggestive, not conclusive, more data is needed."
            )
        )
    else:
        st.markdown(
            f"**t = {timepoint} no population significant at p < {ALPHA}.**"
        )

    with st.expander("All timepoints at once"):
        st.dataframe(stats, width="stretch", hide_index=True)
        for t in TIMEPOINTS:
            t_stats = stats[stats["timepoint"] == t]
            hits = t_stats.loc[t_stats["significant"], "population"].tolist()
            bonf = t_stats.loc[
                t_stats["p_value_bonferroni"] < ALPHA, "population"
            ].tolist()
            st.markdown(
                f"- **t = {t}**: raw p < {ALPHA}: "
                f"{', '.join(hits) if hits else 'none'}; "
                f"after Bonferroni: {', '.join(bonf) if bonf else 'none'}."
            )


# ---- Part 4 -------------------------------------------------------------
with tab_baseline:

    subset = baseline_subset()
    summary = summarize_baseline_subset(subset)
    total_subjects = int(subset["subject_id"].nunique())

    # ---- Part A ------------------------------------------------------------
    st.subheader("Baseline melanoma / miraclib / PBMC samples")
    st.markdown(
        "Samples matching **all** of: `condition = melanoma`, "
        "`treatment = miraclib`, `sample_type = PBMC`, and "
        "`time_from_treatment_start = 0` (the pre-treatment baseline draw)."
    )

    a1, a2 = st.columns(2)
    a1.metric("Baseline samples", f"{len(subset):,}")
    a2.metric("Distinct subjects", f"{total_subjects:,}")

    st.markdown("**Samples per project** How many baseline samples each source project contributed:")
    st.dataframe(
        summary["by_project"].rename("n_samples").reset_index(),
        width="stretch",
        hide_index=True,
    )

    st.markdown(
        "**Subjects by response** distinct subjects (not samples) in each "
        "response group, i.e. how the baseline cohort splits into people whose "
        "disease responded to miraclib vs. not:"
    )
    by_response = summary["by_response"]
    r_cols = st.columns(len(by_response))
    for col, (label, value) in zip(r_cols, by_response.items()):
        pretty = {"yes": "Responders", "no": "Non-responders"}.get(label, label)
        col.metric(pretty, int(value), help=f"response = '{label}'")

    st.markdown("**Subjects by sex** distinct subjects of each sex in the same baseline cohort:")
    by_sex = summary["by_sex"]
    s_cols = st.columns(len(by_sex))
    for col, (label, value) in zip(s_cols, by_sex.items()):
        pretty = {"M": "Male", "F": "Female"}.get(label, label)
        col.metric(pretty, int(value), help=f"sex = '{label}'")


    with st.expander("Show the baseline subset rows"):
        st.dataframe(subset, width="stretch", hide_index=True)

    st.divider()

    # ---- Part B ------------------------------------------------------------
    st.subheader("Average baseline B-cell count")
    st.markdown(
        "*Considering melanoma males of all sample and treatment types, what is "
        "the average number of B cells for responders at time = 0?*\n\n"
        "Filters: `condition = melanoma`, `sex = M`, `response = yes`, "
        "`time_from_treatment_start = 0`. **No** restriction on `sample_type` or "
        "`treatment` — every sample type and treatment arm counts. The average "
        "is taken over the raw `b_cell` counts of all matching samples."
    )
    st.metric("Average B cells (melanoma · male · responder · baseline)", f"{avg_bcell():.2f}")
