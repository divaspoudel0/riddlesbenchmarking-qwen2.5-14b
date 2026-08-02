from __future__ import annotations
from text_features import REPO_ROOT,FIGURES_DIR
from load_survey_data import *
import sys
sys.path.insert(0,str(REPO_ROOT))
from analysis.style import apply_style, save_figure, PALETTE, CATEGORICAL_CYCLE
import numpy as np

import matplotlib.pyplot as plt

df= load_survey_data()


def within_confidence():
    candidates= {
        "Swahili\nKenya"     : "Swahili_Kenya",
        "Telugu\nIndia"      : "Telugu_India",
        "Persian\nIran"      : "Persian_Iran",
        "Bengali\nIndia"     : "Bengali_India",
        "Bengali\nBangladesh": "Bengali_Bangladesh",
        "Portuguese\nBrazil" : "Portuguese_Brazil",

    }

    labels, conf_m, diff_m= [], [], []
    for short,comm in candidates.items():
        sub= df[df["community"]==comm]
        if len(sub)>=2:
            labels.append(short)
            conf_m.append(sub["confidence"].mean())
            diff_m.append(sub["difficulty_overall"].mean())


    x,w= np.arange(len(labels)), 0.35
    fig,ax= plt.subplots(figsize=(8.5,5))
    b1 = ax.bar(x - w / 2, conf_m, w, label="Confidence (mean)", color=PALETTE['blue'])
    b2 = ax.bar(x + w / 2, diff_m, w, label="Overall difficulty (mean)", color=PALETTE['vermillion'])

    ax.set_xticks(x)
    ax.set_xticklabels(labels,fontsize=8)
    ax.set_ylim(0,5.8)
    ax.set_ylabel("Mean rating (1-5)")
    ax.legend(fontsize=8)
    ax.set_title("Within-Community Contributors: Confidence vs Difficulty\n"
        "Survey Q: Confidence rating + "
        '"How would you rate the overall difficulty?"',
        fontsize=9)

    for bar in list(b1)+list(b2):
        ax.text(
            bar.get_x() +bar.get_width()/2,
            bar.get_height()+0.1,
            f"{bar.get_height():.1f}",
            ha="center", fontsize=7,
        )

    save_figure(fig, FIGURES_DIR/"within_community")

