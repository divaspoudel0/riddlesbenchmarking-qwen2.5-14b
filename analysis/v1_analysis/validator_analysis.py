from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from text_features import (
    CSV_DIR,
    FIGURES_DIR,
    MIN_RATINGS_FOR_OUTCOME_CHART,
    REPO_ROOT,
    display_label,
    reconcile_score_label,
)

sys.path.insert(0, str(REPO_ROOT))
from analysis.style import PALETTE, apply_style, save_figure  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

OUTCOME_ORDER = ["correct", "partial", "uncertain", "incorrect"]
OUTCOME_COLORS = {
    "correct": PALETTE["bluish_green"],
    "partial": PALETTE["yellow"],
    "uncertain": PALETTE["sky_blue"],
    "incorrect": PALETTE["vermillion"],
}


def build_outcomes(consolidated: pd.DataFrame) -> pd.DataFrame:
    outcomes = consolidated[["community", "human_answer_score", "human_validator_name"]].copy()
    outcomes["outcome"] = outcomes["human_answer_score"].map(reconcile_score_label)
    outcomes["has_rating"] = outcomes["outcome"].notna()
    return outcomes


def build_coverage_summary(outcomes: pd.DataFrame) -> pd.DataFrame:
    summary = outcomes.groupby("community").agg(
        n_riddles=("has_rating", "size"),
        n_rated=("has_rating", "sum"),
    ).reset_index()
    summary["validator_coverage"] = summary["n_rated"] / summary["n_riddles"]
    summary["display_label"] = summary["community"].map(display_label)

    pct_correct = (
        outcomes[outcomes["has_rating"]]
        .groupby("community")["outcome"]
        .apply(lambda s: (s == "correct").mean())
        .rename("pct_correct_of_rated")
    )
    summary = summary.merge(pct_correct, on="community", how="left")
    return summary.sort_values("validator_coverage", ascending=False).reset_index(drop=True)


def build_outcome_shares(outcomes: pd.DataFrame, coverage: pd.DataFrame) -> pd.DataFrame:
    qualifying = coverage.loc[coverage["n_rated"] >= MIN_RATINGS_FOR_OUTCOME_CHART, "community"]
    rated = outcomes[outcomes["community"].isin(qualifying) & outcomes["has_rating"]]
    counts = rated.groupby(["community", "outcome"]).size().unstack(fill_value=0).reindex(
        columns=OUTCOME_ORDER, fill_value=0
    )
    shares = counts.div(counts.sum(axis=1), axis=0)
    shares["display_label"] = shares.index.map(display_label)
    shares["n_rated"] = counts.sum(axis=1)
    return shares.reset_index()


def plot_coverage(coverage: pd.DataFrame) -> None:
    apply_style()
    ordered = coverage.sort_values("validator_coverage")
    fig, ax = plt.subplots(figsize=(6.0, 9.5))
    ax.barh(ordered["display_label"], ordered["validator_coverage"], color=PALETTE["blue"], height=0.72)
    ax.set_xlabel("share of riddles with a recorded validator rating")
    ax.set_title("Validator coverage by culture (v1)")
    ax.set_xlim(0, 1)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelsize=6.5)
    fig.tight_layout()
    save_figure(fig, FIGURES_DIR / "fig8_validator_coverage")
    plt.close(fig)


def plot_outcomes(shares: pd.DataFrame) -> None:
    apply_style()
    ordered = shares.sort_values("correct")
    fig, ax = plt.subplots(figsize=(6.2, max(3.0, 0.28 * len(ordered))))
    left = np.zeros(len(ordered))
    for outcome in OUTCOME_ORDER:
        ax.barh(
            ordered["display_label"],
            ordered[outcome],
            left=left,
            color=OUTCOME_COLORS[outcome],
            label=outcome,
            height=0.7,
        )
        left += ordered[outcome].to_numpy()
    ax.set_xlabel("share of rated riddles")
    ax.set_title(f"Human-answer validation outcomes (v1, cultures with ≥{MIN_RATINGS_FOR_OUTCOME_CHART} ratings)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.08), ncol=4, fontsize=7)
    ax.set_xlim(0, 1)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    save_figure(fig, FIGURES_DIR / "fig9_validation_outcomes")
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    consolidated = pd.read_csv(CSV_DIR / "riddles_v1_consolidated.csv")

    outcomes = build_outcomes(consolidated)
    coverage = build_coverage_summary(outcomes)
    coverage.to_csv(CSV_DIR / "validator_coverage_per_culture.csv", index=False)

    shares = build_outcome_shares(outcomes, coverage)
    shares.to_csv(CSV_DIR / "validation_outcomes_per_culture.csv", index=False)

    plot_coverage(coverage)
    plot_outcomes(shares)

    rated = outcomes[outcomes["has_rating"]]
    overall = rated["outcome"].value_counts(normalize=True)
    print(f"cultures with >=1 rating: {(coverage['n_rated'] > 0).sum()} / {len(coverage)}")
    print(f"total rated riddles: {len(rated)}")
    print(overall.to_string())


if __name__ == "__main__":
    main()
