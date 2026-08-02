from __future__ import annotations
from text_features import REPO_ROOT,FIGURES_DIR
from load_survey_data import *
import sys
sys.path.insert(0,str(REPO_ROOT))
from analysis.style import apply_style, save_figure, PALETTE
import matplotlib.pyplot as plt


df= load_survey_data()

def ai_usage_breakdown():
    """ Calculate the usage of AI among respondents"""

    aiu= df['resources_used'].dropna().astype(str)
    test_c= (aiu.str.lower().str.contains("testing difficulty")).sum()
    brain_c= (aiu.str.lower().str.contains("brainstorming")).sum()
    para_c= (aiu.str.lower().str.contains("paraphrasing")).sum()

    labels= [
        "Testing difficulty\n(adversarial QA)",
        "Brainstorming\n(idea generation)",
        "Paraphrasing\n co-writing"
    ]

    vals=[test_c, brain_c, para_c]
    colors=[PALETTE["blue"], PALETTE['vermillion'], PALETTE["yellow"]]

    fig, ax= plt.subplots(figsize=(7,5))
    bars= ax.bar(labels, vals, color=colors)

    ax.set_ylabel(f"Respondents (of {len(df)})")
    ax.set_title(
        "Generative AI breakdown\n"
        'Survey Q: "What resources did you use?" + '
        '"Briefly describe how tools were used."',
        fontsize=9
    )

    for bar,v in zip(bars,vals):
        ax.text(bar.get_x()+ bar.get_width()/2, v+0.3, str(v), ha='center', fontsize=12, fontweight="bold")

    ax.annotate(
            f"Testing ({test_c} is the\n most common AI use)",
            xy=(0,test_c), xytext=(1.25, test_c-5),
            arrowprops= dict(arrowstyle="->", color=PALETTE["vermillion"]), color= PALETTE["black"],fontsize=9
        )

    save_figure(fig, FIGURES_DIR/"ai_usage")


