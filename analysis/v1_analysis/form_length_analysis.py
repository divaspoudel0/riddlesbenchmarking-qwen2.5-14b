from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from text_features import (
    CSV_DIR,
    FIGURES_DIR,
    REPO_ROOT,
    display_label,
    is_first_person,
    is_multiline,
    is_question,
    word_count,
)

sys.path.insert(0, str(REPO_ROOT))
from analysis.style import PALETTE, apply_style, save_figure  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402


def form_bucket(row: pd.Series) -> str:
    person = "1st-person" if row["is_first_person"] else "3rd-person"
    shape = "question" if row["is_question"] else "statement"
    return f"{person} {shape}"


def build_per_riddle_features(consolidated: pd.DataFrame) -> pd.DataFrame:
    features = consolidated[["community", "topic_raw", "is_wildcard", "riddle_english"]].copy()
    features["word_count"] = features["riddle_english"].map(word_count)
    features["is_question"] = features["riddle_english"].map(is_question)
    features["is_first_person"] = features["riddle_english"].map(is_first_person)
    features["is_multiline"] = features["riddle_english"].map(is_multiline)
    features["form"] = features.apply(form_bucket, axis=1)
    return features


def build_per_culture_summary(features: pd.DataFrame) -> pd.DataFrame:
    grouped = features.groupby("community")
    summary = grouped.agg(
        n_riddles=("word_count", "size"),
        mean_word_count=("word_count", "mean"),
        std_word_count=("word_count", "std"),
        frac_question=("is_question", "mean"),
        frac_first_person=("is_first_person", "mean"),
        frac_multiline=("is_multiline", "mean"),
    ).reset_index()
    summary["cv_word_count"] = summary["std_word_count"] / summary["mean_word_count"]
    summary["display_label"] = summary["community"].map(display_label)
    return summary.sort_values("mean_word_count", ascending=False).reset_index(drop=True)


def plot_mean_length_by_culture(summary: pd.DataFrame) -> None:
    apply_style()
    ordered = summary.sort_values("mean_word_count")
    flagged = {"Lusoga_Uganda", "Runyankole_Uganda"}
    colors = [PALETTE["vermillion"] if c in flagged else PALETTE["blue"] for c in ordered["community"]]

    fig, ax = plt.subplots(figsize=(6.0, 9.5))
    ax.barh(ordered["display_label"], ordered["mean_word_count"], color=colors, height=0.72)
    ax.set_xlabel("mean riddle length, English text (words)")
    ax.set_title("Mean riddle length by culture (v1)")
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelsize=6.5)
    fig.tight_layout()
    save_figure(fig, FIGURES_DIR / "fig3_word_count_by_culture")
    plt.close(fig)


def plot_form_distribution(features: pd.DataFrame) -> None:
    apply_style()
    order = ["1st-person question", "1st-person statement", "3rd-person question", "3rd-person statement"]
    counts = (
        features.groupby(["community", "form"]).size().unstack(fill_value=0).reindex(columns=order, fill_value=0)
    )
    shares = counts.div(counts.sum(axis=1), axis=0)
    shares["display_label"] = shares.index.map(display_label)
    shares = shares.sort_values(order[0])
    colors = [PALETTE["blue"], PALETTE["sky_blue"], PALETTE["vermillion"], PALETTE["orange"]]

    fig, ax = plt.subplots(figsize=(6.4, 9.5))
    left = np.zeros(len(shares))
    for form_name, color in zip(order, colors):
        ax.barh(shares["display_label"], shares[form_name], left=left, color=color, label=form_name, height=0.72)
        left += shares[form_name].to_numpy()
    ax.set_xlabel("share of riddles")
    ax.set_title("Riddle form/phrasing-style mix by culture (v1)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.06), ncol=2, fontsize=6.5)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelsize=6.5)
    ax.set_xlim(0, 1)
    fig.tight_layout()
    save_figure(fig, FIGURES_DIR / "fig4_form_distribution_by_culture")
    plt.close(fig)


def plot_length_homogeneity(summary: pd.DataFrame) -> None:
    apply_style()
    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    ax.scatter(summary["mean_word_count"], summary["cv_word_count"], color=PALETTE["blue"], s=18)
    for _, row in summary.iterrows():
        if row["cv_word_count"] > summary["cv_word_count"].quantile(0.85) or row["mean_word_count"] > summary[
            "mean_word_count"
        ].quantile(0.9):
            ax.annotate(
                row["display_label"],
                (row["mean_word_count"], row["cv_word_count"]),
                fontsize=6,
                color=PALETTE["grey"],
                xytext=(3, 3),
                textcoords="offset points",
            )
    ax.set_xlabel("mean riddle length (words)")
    ax.set_ylabel("coefficient of variation of riddle length")
    ax.set_title("Within-culture length homogeneity vs. mean length (v1)")
    fig.tight_layout()
    save_figure(fig, FIGURES_DIR / "fig5_length_homogeneity")
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    consolidated = pd.read_csv(CSV_DIR / "riddles_v1_consolidated.csv")

    features = build_per_riddle_features(consolidated)
    features.to_csv(CSV_DIR / "riddle_form_length_per_riddle.csv", index=False)

    summary = build_per_culture_summary(features)
    summary.to_csv(CSV_DIR / "riddle_form_length_per_culture.csv", index=False)

    plot_mean_length_by_culture(summary)
    plot_form_distribution(features)
    plot_length_homogeneity(summary)

    print(summary[["community", "n_riddles", "mean_word_count", "cv_word_count"]].to_string(index=False))


if __name__ == "__main__":
    main()
