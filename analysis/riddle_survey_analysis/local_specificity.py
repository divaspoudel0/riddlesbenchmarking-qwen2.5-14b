from __future__ import annotations
from load_survey_data import load_survey_data
from text_features import REPO_ROOT, FIGURES_DIR
import sys
sys.path.insert(0, str(REPO_ROOT))
from analysis.style import PALETTE, CONDITION_COLORS, apply_style, save_figure
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from collections import Counter

df= load_survey_data()


def calculate_local_specificity():
    """Used to tally broad,local and regional specificity of riddles
    as mentioned by the respondents"""

    short_label_map={
         "Mostly known across the whole national-linguistic community":"Mostly National",
        "Many require regional or local knowledge":"Mostly Regional",
        "Some are broadly known, some are region-specific":"Mixed broad/regional",
        "Many require specialized, older, or niche knowledge":"Niche/specialized"

    }
    labels= list(short_label_map.values())
    counts= df["local_specificity"].dropna().value_counts()
    vals= [counts.get(l,0) for l in short_label_map]
    ordered= sorted(zip(labels,vals), key=lambda x: -x[1])

    labs,vs= zip(*ordered)

    colors= [PALETTE["vermillion"], PALETTE["blue"], PALETTE["orange"], PALETTE["bluish_green"] ]

    fig,ax= plt.subplots(figsize=(7,4.5))
    ax.barh(labs[::-1],vs[::-1], color= colors[::-1])
    ax.set_xlabel(f"Respondents (n = {sum(vals)})")
    ax.set_title(
        "Self-Reported Local Specificity\n"
        'Survey Q: "How locally specific are your riddles overall?"',
        fontsize=9,
    )
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.2, i, str(v), va="center", fontweight="bold")
    save_figure(fig, FIGURES_DIR/"local_specificity")



