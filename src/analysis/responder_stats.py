"""Part 3  responders vs non responders, by timepoint.

For melanoma patients treated with miraclib (PBMC samples), for each of the 5
cell populations AND each timepoint (0, 7, 14 days), tests whether per sample
percentage differs between responders and non responders (Mann Whitney U,
two-sided). Each timepoint gives one independent observation per subject, so
no test pools repeated measures from the same subject.

    python -m src.analysis.responder_stats
        -> output/part3_stats_results.csv       (all timepoints, one row per population x timepoint)
        -> output/part3_responder_summary.txt
        -> output/part3_boxplot_t0.png
        -> output/part3_boxplot_t7.png
        -> output/part3_boxplot_t14.png
"""

import sqlite3

import pandas as pd
from scipy.stats import mannwhitneyu

from src.helpers import ResponderComparison
from src.paths import (
    DB_PATH,
    OUTPUT_DIR,
    RESPONDER_SUMMARY_PATH,
    STATS_RESULTS_PATH,
    ensure_output_dir,
)
import os

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
TIMEPOINTS = [0, 7, 14]
ALPHA = 0.05
N_TESTS = len(POPULATIONS) * len(TIMEPOINTS)  # 15 - corrected globally, not per timepoint

RESPONSE_ORDER = ["no", "yes"]
RESPONSE_COLORS = {"no": "#636EFA", "yes": "#EF553B"}


def boxplot_path(timepoint: int):
    return os.path.join(OUTPUT_DIR, f"part3_boxplot_t{timepoint}.png")


def make_boxplot(df: pd.DataFrame, timepoint: int):
    """Return a plotly Figure of percentage by response, one facet per population.

    Used by the dashboard for the interactive chart. `df` should already be
    filtered to a single timepoint.
    """
    import plotly.express as px

    fig = px.box(
        df,
        x="response",
        y="percentage",
        color="response",
        facet_col="population",
        facet_col_wrap=5,
        category_orders={"response": RESPONSE_ORDER},
        points="all",
        title=f"Cell population % by response (melanoma, miraclib, PBMC, t={timepoint})",
    )
    fig.update_yaxes(matches=None)
    fig.update_layout(width=1500, height=500)
    return fig


def save_boxplot(df: pd.DataFrame, timepoint: int, path) -> None:
    """Render the same boxplot to a PNG with matplotlib (no browser needed).

    One subplot per population, two boxes (no / yes) with the individual sample
    points jittered on top; each subplot keeps its own y-scale. `df` should
    already be filtered to a single timepoint.
    """
    import matplotlib

    matplotlib.use("Agg")  # headless, file-only backend
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(
        1, len(POPULATIONS), figsize=(4 * len(POPULATIONS), 5)
    )
    rng = np.random.default_rng(0)

    for ax, population in zip(axes, POPULATIONS):
        pop = df[df["population"] == population]
        groups = [
            pop.loc[pop["response"] == r, "percentage"].to_numpy()
            for r in RESPONSE_ORDER
        ]

        boxes = ax.boxplot(
            groups, tick_labels=RESPONSE_ORDER, showfliers=False, patch_artist=True
        )
        for patch, r in zip(boxes["boxes"], RESPONSE_ORDER):
            patch.set_facecolor(RESPONSE_COLORS[r])
            patch.set_alpha(0.35)

        for i, (r, vals) in enumerate(zip(RESPONSE_ORDER, groups), start=1):
            ax.scatter(
                rng.normal(i, 0.04, size=len(vals)), vals,
                s=6, color=RESPONSE_COLORS[r], alpha=0.5, linewidths=0,
            )

        ax.set_title(population)
        ax.set_xlabel("response")

    axes[0].set_ylabel("percentage")
    fig.suptitle(f"Cell population % by response (melanoma, miraclib, PBMC, t={timepoint})")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def run_significance_tests(df: pd.DataFrame) -> pd.DataFrame:
    """Mann Whitney U test per (population, timepoint), responders vs non responders.

    `df` must contain columns: population, percentage, response,
    time_from_treatment_start. Bonferroni correction is applied across ALL
    population x timepoint tests (n=15), not per timepoint, since that's the
    real number of comparisons being made.
    """
    rows = []
    for timepoint in TIMEPOINTS:
        tp = df[df["time_from_treatment_start"] == timepoint]
        for population in POPULATIONS:
            pop = tp[tp["population"] == population]
            responders = pop.loc[pop["response"] == "yes", "percentage"]
            non_responders = pop.loc[pop["response"] == "no", "percentage"]

            statistic, p_value = mannwhitneyu(
                responders, non_responders, alternative="two-sided"
            )

            rows.append(
                {
                    "timepoint": timepoint,
                    "population": population,
                    "n_responders": int(responders.size),
                    "n_non_responders": int(non_responders.size),
                    "statistic": round(float(statistic), 2),
                    "p_value": round(float(p_value), 4),
                    "significant": bool(p_value < ALPHA),
                    "p_value_bonferroni": round(min(float(p_value) * N_TESTS, 1.0), 4),
                }
            )

    return pd.DataFrame(rows)


def _format_summary(stats: pd.DataFrame) -> str:
    """Build the human-readable results summary (printed and saved to file)."""
    lines = [
        "Mann Whitney U (responder vs non responder), melanoma / miraclib / PBMC,",
        f"by timepoint. Bonferroni correction applied across all {N_TESTS} tests "
        f"({len(POPULATIONS)} populations x {len(TIMEPOINTS)} timepoints).",
        "",
    ]

    for timepoint in TIMEPOINTS:
        tp_stats = stats[stats["timepoint"] == timepoint]
        hits = tp_stats.loc[tp_stats["significant"], "population"].tolist()
        bonf = tp_stats.loc[tp_stats["p_value_bonferroni"] < ALPHA, "population"].tolist()
        lines.extend(
            [
                f"--- t = {timepoint} ---",
                tp_stats.drop(columns="timepoint").to_string(index=False),
                f"Significant at raw p < {ALPHA}: {', '.join(hits) if hits else 'none'}",
                f"Still significant after Bonferroni (x{N_TESTS}): "
                f"{', '.join(bonf) if bonf else 'none'}",
                "",
            ]
        )

    return "\n".join(lines)


def run_stats():
    """Generate the Part 3 stats table, summary text, and boxplots (one per timepoint)."""
    ensure_output_dir()

    with sqlite3.connect(DB_PATH) as conn:
        df = ResponderComparison().run(conn)

    if "time_from_treatment_start" not in df.columns:
        raise ValueError(
            "ResponderComparison must include time_from_treatment_start - "
            "add s.time_from_treatment_start to its SELECT in helpers.py"
        )

    stats = run_significance_tests(df)
    stats.to_csv(STATS_RESULTS_PATH, index=False)
    print(f"Wrote {STATS_RESULTS_PATH}\n")

    summary = _format_summary(stats)
    print(summary)
    with open(RESPONDER_SUMMARY_PATH, "w", encoding="utf-8") as fh:
        fh.write(summary + "\n")
    print(f"\nWrote {RESPONDER_SUMMARY_PATH}")

    for timepoint in TIMEPOINTS:
        tp_df = df[df["time_from_treatment_start"] == timepoint]
        path = boxplot_path(timepoint)
        save_boxplot(tp_df, timepoint, path)
        print(f"Wrote {path}")


if __name__ == "__main__":
    run_stats()