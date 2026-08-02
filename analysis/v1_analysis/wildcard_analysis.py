from __future__ import annotations

import sys

import pandas as pd

from text_features import CSV_DIR, FIGURES_DIR, REPO_ROOT, display_label, themes_for_topic_label

sys.path.insert(0, str(REPO_ROOT))
from analysis.style import PALETTE, apply_style, save_figure  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402


def build_choices_table(consolidated: pd.DataFrame) -> pd.DataFrame:
    choices = (
        consolidated.loc[consolidated["is_wildcard"], ["community", "wildcard_topic"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    choices["themes"] = choices["wildcard_topic"].map(themes_for_topic_label)
    choices["theme_list"] = choices["themes"].map(lambda ts: "; ".join(ts) if ts else "Other / culture-specific")
    return choices


def build_theme_popularity(choices: pd.DataFrame) -> pd.DataFrame:
    exploded = choices.explode("themes")
    exploded["themes"] = exploded["themes"].fillna("Other / culture-specific")
    total_communities = choices["community"].nunique()
    counts = (
        exploded.groupby("themes")["community"]
        .nunique()
        .sort_values(ascending=False)
        .rename("n_communities")
        .reset_index()
        .rename(columns={"themes": "theme"})
    )
    counts["share_of_communities"] = counts["n_communities"] / total_communities
    return counts


def build_reuse_table(choices: pd.DataFrame) -> pd.DataFrame:
    normalized = choices.copy()
    normalized["norm_topic"] = normalized["wildcard_topic"].str.strip().str.casefold()
    grouped = normalized.groupby("norm_topic").agg(
        wildcard_name=("wildcard_topic", "first"),
        n_communities=("community", "nunique"),
        communities=("community", lambda s: ", ".join(sorted(display_label(c) for c in s.unique()))),
    )
    reused = grouped[grouped["n_communities"] > 1].sort_values("n_communities", ascending=False)
    return reused.reset_index(drop=True)[["wildcard_name", "n_communities", "communities"]]


def plot_theme_popularity(theme_counts: pd.DataFrame, top_n: int = 12) -> None:
    apply_style()
    top = theme_counts.head(top_n).sort_values("n_communities")
    top_theme = theme_counts.iloc[0]["theme"]
    colors = [PALETTE["vermillion"] if t == top_theme else PALETTE["blue"] for t in top["theme"]]

    fig, ax = plt.subplots(figsize=(5.4, 4.4))
    ax.barh(top["theme"], top["n_communities"], color=colors, height=0.7)
    ax.set_xlabel("number of communities choosing this wildcard theme")
    ax.set_title("Most popular wildcard themes across cultures (v1)")
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    for y, count in enumerate(top["n_communities"]):
        ax.text(count + 0.1, y, str(count), va="center", fontsize=8, color=PALETTE["grey"])
    fig.tight_layout()
    save_figure(fig, FIGURES_DIR / "fig1_wildcard_themes")
    plt.close(fig)


def plot_top_theme_share(theme_counts: pd.DataFrame, choices: pd.DataFrame) -> None:
    apply_style()
    top_theme = theme_counts.iloc[0]["theme"]
    total = choices["community"].nunique()
    top_n_communities = int(theme_counts.iloc[0]["n_communities"])
    share = pd.Series(
        {top_theme: top_n_communities, "All other themes": total - top_n_communities}
    )

    fig, ax = plt.subplots(figsize=(4.8, 2.4))
    ax.barh(share.index, share.values, color=[PALETTE["vermillion"], PALETTE["light_grey"]], height=0.6)
    ax.set_xlabel(f"number of communities (out of {total})")
    ax.set_title(f'"{top_theme}" vs. every other wildcard theme')
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    for y, count in enumerate(share.values):
        ax.text(count + 0.4, y, str(count), va="center", fontsize=8, color=PALETTE["grey"])
    fig.tight_layout()
    save_figure(fig, FIGURES_DIR / "fig2_top_theme_share")
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    consolidated = pd.read_csv(CSV_DIR / "riddles_v1_consolidated.csv")

    choices = build_choices_table(consolidated)
    choices.drop(columns=["themes"]).to_csv(CSV_DIR / "wildcard_choices.csv", index=False)

    theme_counts = build_theme_popularity(choices)
    theme_counts.to_csv(CSV_DIR / "wildcard_theme_popularity.csv", index=False)

    reuse_table = build_reuse_table(choices)
    reuse_table.to_csv(CSV_DIR / "wildcard_reuse_table.csv", index=False)

    plot_theme_popularity(theme_counts)
    plot_top_theme_share(theme_counts, choices)

    print(theme_counts.to_string(index=False))
    print(f"\nreused wildcard names: {len(reuse_table)}")


if __name__ == "__main__":
    main()
