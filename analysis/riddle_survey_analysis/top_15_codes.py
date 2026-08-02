from __future__ import annotations
from text_features import REPO_ROOT,FIGURES_DIR, CSV_DIR
from load_survey_data import *
import sys
sys.path.insert(0,str(REPO_ROOT))
from analysis.style import apply_style, save_figure, PALETTE, CATEGORICAL_CYCLE
import numpy as np

import matplotlib.pyplot as plt

def top_codes():
    path= CSV_DIR/"[MCB]_Analysis_MasterSheet - Code_Frequency_Reference.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")

    df= pd.read_csv(path)
    df.columns= [c.strip() for c in df.columns]
    code_col, freq_col= df.columns[0], df.columns[1]
    df[freq_col]= pd.to_numeric(df[freq_col], errors="coerce")
    df= df.dropna(subset=[freq_col]).sort_values(freq_col, ascending=False).head(15)

    fig,ax= plt.subplots(figsize=(9,6))
    ax.barh(df[code_col].tolist()[::-1], df[freq_col].tolist()[::-1], color=PALETTE['blue'])
    ax.set_xlabel("Total code mentions across all questions")
    ax.set_title(
        f"Top 15 Most Frequent Codes  "
        f"({len(pd.read_csv(path))} unique codes total)",
        fontsize=9,
    )
    for i, v in enumerate(df[freq_col].tolist()[::-1]):
        ax.text(v + 0.3, i, str(int(v)), va="center")

    save_figure(fig, FIGURES_DIR/"top_codes")


