"""Part 3  responders vs non responders.

For melanoma patients treated with miraclib (PBMC samples), for each of the 5
cell populations, tests whether per-sample percentage differs between responders
and non responders (Mann Whitney U, two-sided).

    python -m src.analysis.responder_stats
        -> output/part3_stats_results.csv
        -> output/part3_responder_summary.txt
        -> output/part3_boxplot.png
"""

import sqlite3

import pandas as pd
from scipy.stats import mannwhitneyu

from src.helpers import ResponderComparison
from src.paths import (
    BOXPLOT_PATH,
    DB_PATH,
    RESPONDER_SUMMARY_PATH,
    STATS_RESULTS_PATH,
    ensure_output_dir,
)

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
ALPHA = 0.05        # threshold for p value
N_TESTS = len(POPULATIONS)


RESPONSE_ORDER = ["no", "yes"]
RESPONSE_COLORS = {"no": "#636EFA", "yes": "#EF553B"}


def make_boxplot(df):
    """Return a plotly Figure of percentage by response, one facet per population.

    Used by the dashboard for the interactive chart.
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
        title="Cell population % by response (melanoma, miraclib, PBMC)",
    )
    fig.update_yaxes(matches=None)
    fig.update_layout(width=1500, height=500)
    return fig


def save_boxplot(df: pd.DataFrame, path) -> None:
    """Render the same boxplot to a PNG with matplotlib (no browser needed).

    One subplot per population, two boxes (no / yes) with the individual sample
    points jittered on top; each subplot keeps its own y-scale.
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
    fig.suptitle("Cell population % by response (melanoma, miraclib, PBMC)")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def run_significance_tests(df: pd.DataFrame) -> pd.DataFrame:
    """Mann Whitney U test per population, responders vs non responders.

    Columns: population, n_responders, n_non_responders, statistic, p_value,
    significant (p_value < 0.05), p_value_bonferroni.
    """
    rows = []
    for population in POPULATIONS:
        pop = df[df["population"] == population]
        responders = pop.loc[pop["response"] == "yes", "percentage"]
        non_responders = pop.loc[pop["response"] == "no", "percentage"]

        statistic, p_value = mannwhitneyu(
            responders, non_responders, alternative="two-sided"
        )

        rows.append(
            {
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
    hits = stats.loc[stats["significant"], "population"].tolist()
    bonf = stats.loc[stats["p_value_bonferroni"] < ALPHA, "population"].tolist()
    return "\n".join(
        [
            "Mann Whitney U (responder vs non responder), "
            "melanoma / miraclib / PBMC:",
            stats.to_string(index=False),
            "",
            f"Significant at raw p < {ALPHA}: "
            f"{', '.join(hits) if hits else 'none'}",
            f"Still significant after Bonferroni (x{N_TESTS}): "
            f"{', '.join(bonf) if bonf else 'none'}",
        ]
    )


def run_stats():
    """Generate the Part 3 stats table, summary text, and boxplot image."""
    ensure_output_dir()

    with sqlite3.connect(DB_PATH) as conn:
        df = ResponderComparison().run(conn)

    stats = run_significance_tests(df)
    stats.to_csv(STATS_RESULTS_PATH, index=False)
    print(f"Wrote {STATS_RESULTS_PATH}\n")

    summary = _format_summary(stats)
    print(summary)
    with open(RESPONDER_SUMMARY_PATH, "w", encoding="utf-8") as fh:
        fh.write(summary + "\n")
    print(f"\nWrote {RESPONDER_SUMMARY_PATH}")

    save_boxplot(df, BOXPLOT_PATH)
    print(f"\nWrote {BOXPLOT_PATH}")


if __name__ == "__main__":
    run_stats()
