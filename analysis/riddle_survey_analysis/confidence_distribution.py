from __future__ import annotations
from text_features import REPO_ROOT,FIGURES_DIR
from load_survey_data import *
import sys
sys.path.insert(0,str(REPO_ROOT))
from analysis.style import apply_style, save_figure, PALETTE
import matplotlib.pyplot as plt

df= load_survey_data()

def confidence_distribution():
    conf=  df["confidence"].dropna()
    cc= conf.value_counts().sort_index()

    fig,ax= plt.subplots(figsize=(6,4.5))
    ax.bar(cc.index.astype(str),cc.values, color= PALETTE['sky_blue'])
    ax.set_xlabel("Confidence (1=low, 5=high)")
    ax.set_ylabel("Respondents")
    ax.set_title(
        f"Confidence in Community Representation (mean= {conf.mean():.2f})\n"
        'Survey Q:"How confident are you that your riddles affect your community?"',
        fontsize=9
    )

    for x,v in zip(cc.index, cc.values):
        ax.text(str(x), v+0.2, str(v), ha="center", fontweight="bold")

    save_figure(fig, FIGURES_DIR/"confidence_distribution")

