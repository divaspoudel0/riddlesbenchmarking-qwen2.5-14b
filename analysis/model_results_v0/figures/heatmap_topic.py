"""Figure 2: model x topic accuracy heatmap (automatic eval).

Pure function `make_topic_heatmap(df) -> fig` plus CLI saving PDF + PNG.
Models sorted by overall accuracy (best on top); topics in a fixed order so
the figure is comparable across versions. Cell values annotated (grid is
small enough to read).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import re

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

# The dataset has 8 fixed topics every community wrote (10 riddles each),
# plus 2 free-named wildcard slots per community. instance_topic holds
# community-specific free text, so the canonical topic is derived from
# riddle_id ({community}_{topic}_{number}); anything outside the fixed set
# is bucketed as Wildcard.
FIXED_TOPICS = [
    "arts",
    "everyday_life",
    "geography",
    "history",
    "kids_world",
    "national_heritage",
    "politics",
    "sports",
]
TOPIC_LABELS = {
    "arts": "Arts",
    "everyday_life": "Everyday life",
    "geography": "Geography",
    "history": "History",
    "kids_world": "Kids' world",
    "national_heritage": "National heritage",
    "politics": "Politics",
    "sports": "Sports",
    "wildcard": "Wildcard",
}


def canonical_topic(riddle_id: str, community: str) -> str:
    slug = riddle_id
    if slug.startswith(community + "_"):
        slug = slug[len(community) + 1:]
    slug = re.sub(r"_\d+$", "", slug)
    return slug if slug in FIXED_TOPICS else "wildcard"


def make_topic_heatmap(df: pd.DataFrame):
    style.apply_style()
    if "is_completed" not in df.columns:
        df = add_derived_columns(df)

    completed = df[df.is_completed].copy()
    completed["topic"] = [
        canonical_topic(r, c)
        for r, c in zip(completed.riddle_id, completed.instance_community)
    ]

    # accuracy per (model, topic), over completed responses
    acc = (
        completed.groupby(["model_display", "topic"])["is_correct"]
        .mean()
        .unstack("topic")
        .mul(100)
    )

    topics = FIXED_TOPICS + ["wildcard"]
    acc = acc[[t for t in topics if t in acc.columns]]
    acc.columns = [TOPIC_LABELS[t] for t in acc.columns]

    # row order: overall accuracy, best on top
    order = model_summary(df).index  # already sorted desc
    acc = acc.loc[[m for m in order if m in acc.index]]

    fig, ax = plt.subplots(figsize=(6.5, 8.5))
    im = ax.imshow(acc.to_numpy(), cmap=style.SEQUENTIAL_CMAP, aspect="auto",
                   vmin=0, vmax=float(np.nanmax(acc.to_numpy())))

    search_models = search_model_set(df)
    ylabels = [label_with_search(m, search_models) for m in acc.index]
    ax.set_xticks(range(len(acc.columns)), acc.columns, rotation=35,
                  ha="right")
    ax.set_yticks(range(len(acc.index)), ylabels)
    ax.grid(visible=False)

    # annotate cells; flip text color on dark cells for readability
    vmax = float(np.nanmax(acc.to_numpy()))
    for i in range(acc.shape[0]):
        for j in range(acc.shape[1]):
            v = acc.iat[i, j]
            if np.isnan(v):
                continue
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7,
                    color="white" if v < 0.55 * vmax else "black")

    fig.colorbar(im, ax=ax, shrink=0.6,
                 label="Accuracy over completed responses (%)")
    ax.set_title("v0 accuracy by model and topic, automatic evaluation")
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
    fig = make_topic_heatmap(df)
    out = Path("figures/out/heatmap_topic")
    style.save_figure(fig, out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight")
    print(f"Wrote {out}.pdf and {out}.png")


if __name__ == "__main__":
    main()
