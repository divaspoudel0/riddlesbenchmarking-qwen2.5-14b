from __future__ import annotations
from text_features import FIGURES_DIR,REPO_ROOT

import sys
sys.path.insert(0,str(REPO_ROOT))
from analysis.style import apply_style, save_figure, PALETTE
from load_survey_data import *
import matplotlib.pyplot as plt
import pandas as pd


df= load_survey_data()

def time_per_riddle():
    """ Calculates and plots the time taken per riddle """
    short_label_map={
        "Less than 5 minutes": "<5 min",
        "5-10 minutes": "5-10 min",
        "10-15 minutes": "10-15 min",
        "More than 15 minutes": ">15 min",
        "More than 30 minutes": ">30 min",
        "It varied too much to estimate": "Varied"
    }

    label= list(short_label_map.values())
    tpr= df["time_per_riddle"].dropna().value_counts()
    vals= [tpr.get(t,0) for t in short_label_map.keys()]
    ordered= zip(label,vals)

    labs,vs= zip(*ordered)
    fig, ax= plt.subplots(figsize=(7,5))
    bars= ax.bar(labs,vs, color= PALETTE["blue"])
    ax.set_ylabel("Respondents")
    ax.set_title(
        "Time per Riddle\n"
        'Survey Q: "On average, How long did it take to write one complete riddle?"',
        fontsize=9
    )

    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.2,
                str(v), ha="center", fontweight="bold")

    save_figure(fig,FIGURES_DIR/"time_per_riddle")


