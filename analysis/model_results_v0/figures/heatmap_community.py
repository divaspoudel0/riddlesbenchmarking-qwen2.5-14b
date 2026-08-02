"""Figure 3: model x community accuracy heatmap (automatic eval).

24 models x 44 communities. Communities sorted by mean accuracy across
models so the gradient carries the story; no cell annotations (grid too
dense). Full grid: paper-body may use a condensed variant later, this is
the appendix/reference version.
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


def make_community_heatmap(df: pd.DataFrame):
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
    # columns: communities by mean accuracy across models (easiest left)
    acc = acc[acc.mean(axis=0).sort_values(ascending=False).index]

    fig, ax = plt.subplots(figsize=(11, 6.5))
    im = ax.imshow(acc.to_numpy(), cmap=style.SEQUENTIAL_CMAP, aspect="auto",
                   vmin=0, vmax=float(np.nanmax(acc.to_numpy())))

    search_models = search_model_set(df)
    ylabels = [label_with_search(m, search_models) for m in acc.index]
    ax.set_xticks(range(len(acc.columns)), acc.columns, rotation=60,
                  ha="right", fontsize=6.5)
    ax.set_yticks(range(len(acc.index)), ylabels, fontsize=7.5)
    ax.grid(visible=False)

    fig.colorbar(im, ax=ax, shrink=0.7, pad=0.01,
                 label="Accuracy over completed responses (%)")
    ax.set_title(
        "v0 accuracy by model and community, automatic evaluation "
        "(communities sorted by mean accuracy)"
    )
    if search_models:
        fig.text(0.01, 0.005, SEARCH_NOTE, fontsize=7,
                 color=style.PALETTE["grey"])
        fig.tight_layout(rect=(0, 0.03, 1, 1))
    else:
        fig.tight_layout()
    return fig


def main() -> None:
    parquet = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "data/processed/results_tidy.parquet"
    )
    df = pd.read_parquet(parquet)
    fig = make_community_heatmap(df)
    out = Path("figures/out/heatmap_community")
    style.save_figure(fig, out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight")
    print(f"Wrote {out}.pdf and {out}.png")


if __name__ == "__main__":
    main()
