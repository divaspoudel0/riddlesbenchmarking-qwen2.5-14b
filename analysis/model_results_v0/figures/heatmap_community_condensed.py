"""Figure 3 (paper body): condensed model x community accuracy heatmap.

The full 44-community grid (heatmap_community.py) stays as the appendix
figure; this paper-body version keeps only the extremes: the N easiest and
N hardest communities by mean accuracy across models, with a visual gap
marking the omitted middle. The spread story survives at single-column
width; the appendix carries the full grid.

Column selection is computed from the data, so the figure self-updates on
rescoring (e.g. the template-echo rerun).

Pure function `make_condensed_community_heatmap(df) -> fig` plus CLI
saving PDF + PNG.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve()
sys.path.append(str(_HERE.parents[2]))  # analysis/
sys.path.append(str(_HERE.parents[1]))  # analysis/model_results_v0/
import style  # noqa: E402
from metrics import (  # noqa: E402
    SEARCH_NOTE,
    add_derived_columns,
    label_with_search,
    model_summary,
    search_model_set,
)

N_EXTREME = 8  # communities kept on each end


def make_condensed_community_heatmap(df: pd.DataFrame, n_extreme: int = N_EXTREME):
    style.apply_style()
    if "is_completed" not in df.columns:
        df = add_derived_columns(df)

    completed = df[df.is_completed]
    acc = (
        completed.groupby(["model_display", "instance_community"])["is_correct"]
        .mean()
        .unstack("instance_community")
        .mul(100)
    )

    # rows: models by overall accuracy (best on top)
    order = model_summary(df).index
    acc = acc.loc[[m for m in order if m in acc.index]]

    # columns: mean accuracy across models, easiest left
    col_order = acc.mean(axis=0).sort_values(ascending=False).index
    n_omitted = len(col_order) - 2 * n_extreme
    easiest = list(col_order[:n_extreme])
    hardest = list(col_order[-n_extreme:])

    # data matrix with a NaN spacer column marking the omitted middle
    left = acc[easiest].to_numpy()
    right = acc[hardest].to_numpy()
    spacer = np.full((acc.shape[0], 1), np.nan)
    mat = np.hstack([left, spacer, right])

    fig, ax = plt.subplots(figsize=(7, 6.5))
    im = ax.imshow(mat, cmap=style.SEQUENTIAL_CMAP, aspect="auto",
                   vmin=0, vmax=float(np.nanmax(mat)))

    search_models = search_model_set(df)
    ylabels = [label_with_search(m, search_models) for m in acc.index]
    xlabels = easiest + [f"... {n_omitted} omitted ..."] + hardest
    ax.set_xticks(range(len(xlabels)), xlabels, rotation=60,
                  ha="right", fontsize=6.5)
    ax.set_yticks(range(len(acc.index)), ylabels, fontsize=7.5)
    ax.grid(visible=False)

    # annotate cells (grid is small enough at 16 columns)
    vmax = float(np.nanmax(mat))
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            if np.isnan(v):
                continue
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=5.5,
                    color="white" if v < 0.55 * vmax else "black")

    fig.colorbar(im, ax=ax, shrink=0.7, pad=0.01,
                 label="Accuracy over completed responses (%)")
    ax.set_title(
        f"v0 accuracy by model, {n_extreme} easiest and {n_extreme} hardest "
        "communities (full grid in appendix)"
    )
    footnote = (
        "Communities ranked by mean accuracy across models; middle omitted "
        "here, full 44-community grid in the appendix."
    )
    if search_models:
        footnote += "\n" + SEARCH_NOTE
    fig.text(0.01, 0.005, footnote, fontsize=7, color=style.PALETTE["grey"])
    fig.tight_layout(rect=(0, 0.045 if search_models else 0.03, 1, 1))
    return fig


def main() -> None:
    parquet = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "data/processed/results_tidy.parquet"
    )
    df = pd.read_parquet(parquet)
    fig = make_condensed_community_heatmap(df)
    out = Path("figures/out/heatmap_community_condensed")
    style.save_figure(fig, out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight")
    print(f"Wrote {out}.pdf and {out}.png")


if __name__ == "__main__":
    main()
