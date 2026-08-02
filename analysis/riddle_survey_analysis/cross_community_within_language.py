from __future__ import annotations
from text_features import REPO_ROOT,FIGURES_DIR
from load_survey_data import *
import sys
sys.path.insert(0,str(REPO_ROOT))
from analysis.style import apply_style, save_figure, PALETTE, CATEGORICAL_CYCLE

import matplotlib.pyplot as plt

df= load_survey_data()

def _grouped_difficulty(
    ax: plt.Axes,
    communities: list[str],
    short_names: list[str],
    df: pd.DataFrame,
    title: str,
    subtitle: str = "",
) :
    x     = np.arange(len(DIFF_LABELS))
    n     = len(communities)
    width = 0.8 / n
    for i, (comm, short) in enumerate(zip(communities, short_names)):
        sub = df[df["community"] == comm]
        if sub.empty:
            print(f" no rows for '{comm}' — bar skipped")
            continue
        vals = [
            sub[c].mean() if not np.isnan(sub[c].mean()) else 0
            for c in DIFF_COLS
        ]
        ax.bar(
            x + (i - n / 2 + 0.5) * width, vals, width,
            label=short, color=CATEGORICAL_CYCLE[i % len(CATEGORICAL_CYCLE)], alpha=0.85,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(DIFF_LABELS, fontsize=8)
    ax.set_ylim(0, 5.8)
    ax.set_ylabel("Mean difficulty (0–5)")
    ax.legend(fontsize=8)
    full = f"{title}\n{subtitle}" if subtitle else title
    ax.set_title(full, fontsize=9)


def arabic_difficuty():
    fig, ax = plt.subplots(figsize=(9, 5.5))
    _grouped_difficulty(
        ax,
        ["Egyptian-Arabic_Egypt", "Moroccan_Morocco", "Syrian_Syria", "Sudanese_Sudan"],
        ["Egypt", "Morocco", "Syria", "Sudan"],
        df,
        "Arabic Communities — Topic Difficulty Comparison",
        "Survey Q: Per-topic 0–5 difficulty rating (1 respondent per community)",
    )
    save_figure(fig, FIGURES_DIR/"arabic_difficulty")

def indonesian_difficulty():
    fig, ax = plt.subplots(figsize=(9, 5.5))
    _grouped_difficulty(
        ax,
        ["Indonesian_Indonesia", "Bugisnese_Indonesia", "Mongondow_Indonesia"],
        ["Indonesian\n(national)", "Bugisnese", "Mongondow"],
        df,
        "Indonesian Language Communities — Topic Difficulty",
        "Survey Q: Per-topic 0–5 difficulty rating; Indonesian n=2, others n=1",
    )
    save_figure(fig, FIGURES_DIR/"indonesian_difficulty")


def bengali_difficulty():
    fig, ax = plt.subplots(figsize=(9, 5.5))
    _grouped_difficulty(
        ax,
        ["Bengali_India", "Bengali_Bangladesh"],
        ["Bengali India (n=3)", "Bengali Bangladesh (n=3)"],
        df,
        "Bengali: India vs Bangladesh — Mean Topic Difficulty",
        "Survey Q: Per-topic 0–5 difficulty rating (n=3 each)",
    )
    save_figure(fig, FIGURES_DIR/"bengali_difficulty")


def portuguese_difficulty():
    fig, ax = plt.subplots(figsize=(9, 5.5))
    _grouped_difficulty(
        ax,
        ["Portuguese_Brazil", "Portuguese_Portugal"],
        ["Portuguese Brazil (n=3)", "Portuguese Portugal (n=1)"],
        df,
        "Portuguese: Brazil vs Portugal — Topic Difficulty",
        "Survey Q: Per-topic 0–5 difficulty rating; Brazil n=3, Portugal n=1",
    )
    save_figure(fig, FIGURES_DIR/"portuguese_difficulty")






