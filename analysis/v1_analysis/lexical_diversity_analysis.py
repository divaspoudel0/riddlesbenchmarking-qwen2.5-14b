from __future__ import annotations

import math
import sys
from collections import Counter

import pandas as pd

from text_features import CSV_DIR, FIGURES_DIR, REPO_ROOT, display_label, tokenize_english, zipf, RARE_ZIPF_THRESHOLD

sys.path.insert(0, str(REPO_ROOT))
from analysis.style import PALETTE, apply_style, save_figure  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402


def build_per_culture_summary(consolidated: pd.DataFrame) -> pd.DataFrame:
    zipf_cache: dict[str, float] = {}

    def cached_zipf(word: str) -> float:
        if word not in zipf_cache:
            zipf_cache[word] = zipf(word)
        return zipf_cache[word]

    rows = []
    for community, group in consolidated.groupby("community"):
        tokens: list[str] = []
        for text in group["riddle_english"].dropna():
            tokens.extend(tokenize_english(text))

        total_tokens = len(tokens)
        type_counts = Counter(tokens)
        n_types = len(type_counts)
        root_ttr = n_types / math.sqrt(total_tokens) if total_tokens else float("nan")
        hapax_ratio = sum(1 for c in type_counts.values() if c == 1) / n_types if n_types else float("nan")
        rare_tokens = sum(1 for t in tokens if cached_zipf(t) < RARE_ZIPF_THRESHOLD)
        rare_fraction = rare_tokens / total_tokens if total_tokens else float("nan")

        rows.append(
            {
                "community": community,
                "display_label": display_label(community),
                "total_tokens": total_tokens,
                "n_types": n_types,
                "root_ttr": root_ttr,
                "hapax_ratio": hapax_ratio,
                "rare_token_fraction": rare_fraction,
            }
        )
    return pd.DataFrame(rows).sort_values("rare_token_fraction", ascending=False).reset_index(drop=True)


def plot_lexical_diversity(summary: pd.DataFrame) -> None:
    apply_style()
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    ax.scatter(summary["root_ttr"], summary["rare_token_fraction"], color=PALETTE["blue"], s=20)
    high_rare = summary["rare_token_fraction"].quantile(0.85)
    high_ttr = summary["root_ttr"].quantile(0.85)
    low_ttr = summary["root_ttr"].quantile(0.1)
    for _, row in summary.iterrows():
        if row["rare_token_fraction"] >= high_rare or row["root_ttr"] >= high_ttr or row["root_ttr"] <= low_ttr:
            ax.annotate(
                row["display_label"],
                (row["root_ttr"], row["rare_token_fraction"]),
                fontsize=6,
                color=PALETTE["grey"],
                xytext=(3, 3),
                textcoords="offset points",
            )
    ax.set_xlabel("root-TTR (vocabulary richness)")
    ax.set_ylabel(f"% tokens rarer than zipf {RARE_ZIPF_THRESHOLD}")
    ax.set_title("Lexical diversity by culture (v1)")
    fig.tight_layout()
    save_figure(fig, FIGURES_DIR / "fig7_lexical_diversity")
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    consolidated = pd.read_csv(CSV_DIR / "riddles_v1_consolidated.csv")

    summary = build_per_culture_summary(consolidated)
    summary.to_csv(CSV_DIR / "lexical_diversity_per_culture.csv", index=False)

    plot_lexical_diversity(summary)

    print(summary[["community", "root_ttr", "rare_token_fraction", "hapax_ratio"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
