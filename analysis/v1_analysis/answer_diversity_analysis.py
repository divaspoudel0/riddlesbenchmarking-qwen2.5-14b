from __future__ import annotations

import sys
from collections import Counter

import pandas as pd

from text_features import (
    CSV_DIR,
    FIGURES_DIR,
    REPO_ROOT,
    display_label,
    entity_like_answer,
    normalize_answer_text,
)

sys.path.insert(0, str(REPO_ROOT))
from analysis.style import PALETTE, apply_style, save_figure  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

TOP_REPEATED_PER_CULTURE = 4
MIN_REPEATS_TO_REPORT = 2


def build_answer_table(consolidated: pd.DataFrame) -> pd.DataFrame:
    table = consolidated[["community", "reference_answer_english"]].copy()
    table["normalized_answer"] = table["reference_answer_english"].map(normalize_answer_text)
    table["entity_like"] = table["reference_answer_english"].map(entity_like_answer)
    return table


def build_per_culture_summary(answers: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for community, group in answers.groupby("community"):
        non_null = group["normalized_answer"].dropna()
        n = len(group)
        n_filled = len(non_null)
        n_unique = non_null.nunique()
        counts = Counter(non_null)
        repeats = sorted(
            ((ans, n_count) for ans, n_count in counts.items() if n_count >= MIN_REPEATS_TO_REPORT),
            key=lambda item: -item[1],
        )[:TOP_REPEATED_PER_CULTURE]
        display_originals = {
            normalize_answer_text(v): v
            for v in group["reference_answer_english"].dropna().unique()
        }
        top_repeated = "; ".join(f"{display_originals.get(a, a)} (x{n_count})" for a, n_count in repeats)
        rows.append(
            {
                "community": community,
                "display_label": display_label(community),
                "n_riddles": n,
                "n_filled_answers": n_filled,
                "answer_fill_rate": n_filled / n if n else float("nan"),
                "n_unique_answers": n_unique,
                "unique_answer_ratio_of_filled": n_unique / n_filled if n_filled else float("nan"),
                "entity_like_ratio": group["entity_like"].mean(),
                "top_repeated_answers": top_repeated,
            }
        )
    return pd.DataFrame(rows).sort_values("unique_answer_ratio_of_filled").reset_index(drop=True)


def plot_unique_ratio(summary: pd.DataFrame, bottom_n: int = 15) -> None:
    apply_style()
    ordered = summary.sort_values("unique_answer_ratio_of_filled").head(bottom_n).sort_values(
        "unique_answer_ratio_of_filled", ascending=False
    )
    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    ax.barh(
        ordered["display_label"], ordered["unique_answer_ratio_of_filled"], color=PALETTE["blue"], height=0.7
    )
    ax.set_xlabel("unique-answer ratio (unique reference answers / filled answers)")
    ax.set_title(f"Least answer-diverse cultures (v1, bottom {bottom_n})")
    ax.set_xlim(0, 1)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    for y, ratio in enumerate(ordered["unique_answer_ratio_of_filled"]):
        ax.text(ratio + 0.01, y, f"{ratio:.0%}", va="center", fontsize=7, color=PALETTE["grey"])
    fig.tight_layout()
    save_figure(fig, FIGURES_DIR / "fig6_answer_diversity")
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    consolidated = pd.read_csv(CSV_DIR / "riddles_v1_consolidated.csv")

    answers = build_answer_table(consolidated)
    summary = build_per_culture_summary(answers)
    summary.to_csv(CSV_DIR / "answer_diversity_per_culture.csv", index=False)

    plot_unique_ratio(summary)

    print(
        summary[
            ["community", "answer_fill_rate", "n_unique_answers", "unique_answer_ratio_of_filled", "entity_like_ratio"]
        ]
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
