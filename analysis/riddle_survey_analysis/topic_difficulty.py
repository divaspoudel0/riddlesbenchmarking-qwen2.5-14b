from __future__ import annotations
from text_features import FIGURES_DIR,REPO_ROOT
import sys
sys.path.insert(0, str(REPO_ROOT))
from load_survey_data import load_survey_data, DIFF_COLS, DIFF_LABELS
from analysis.style import PALETTE, CONDITION_COLORS, apply_style, save_figure
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

df= load_survey_data()


def calculate_topic_difficulty():
    """ Used to tally and generate graphs based on topic difficulty"""
    means= [df[c].dropna().mean() for c in DIFF_COLS]
    ns= [df[c].dropna().__len__() for c in DIFF_COLS]

    order= sorted(zip(DIFF_LABELS,means, ns), key=lambda x: -x[1])

    labels, ms, ns= zip(*order)

    colors= [PALETTE["vermillion"] if m==max(ms) else PALETTE["blue"] for m in ms]

    fig, ax= plt.subplots(figsize=(8.5,5))
    bars= ax.bar(labels,ms,color=colors)
    ax.set_ylabel("Mean Difficulty (0-5)")
    ax.set_ylim(0,5.5)
    ax.set_title(
        "Difficulty by Topic\n"
        'Survey Q: "How Difficult was it to write for each topic,'
        'from 0 to 5?" (0/ N/A excluded; red= hardest)',
        fontsize=9
    )

    for bar,m,n in zip(bars, ms, ns):
        ax.text(bar.get_x() + bar.get_width()/2, m+0.1,
                f"{m:.2f}\n(n={n})", ha= "center", fontsize=7)

    plt.xticks(fontsize=9)

    save_figure(fig,FIGURES_DIR/"topic_difficulty")


