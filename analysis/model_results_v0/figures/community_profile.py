"""Figure: accuracy profiles across all 44 communities (automatic eval).

Alternative to the full community heatmap: communities on the x-axis
sorted easiest to hardest by mean accuracy, one thin grey line per
closed-book model, a few reference models highlighted, and the
cross-model mean in black. Shows the full gradient AND its shape: every
model decays toward zero on the hardest communities; frontier models
just start higher and hold on longer.

Search-enabled runs are excluded (separate evaluation category).

Pure function `make_community_profile(df) -> fig` plus CLI saving
PDF + PNG.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

_HERE = Path(__file__).resolve()
sys.path.append(str(_HERE.parents[2]))  # analysis/
sys.path.append(str(_HERE.parents[1]))  # analysis/model_results_v0/
import style  # noqa: E402
from metrics import (  # noqa: E402
    add_derived_columns,
    model_summary,
    search_model_set,
)

# Models drawn in color; everything else is a thin grey context line.
# Picked to span the range: best frontier, best open-ish mid-size, a
# strong small model, and the community-focused Tiny-Aya family rep.
HIGHLIGHTS: dict[str, str] = {
    "GPT5.5 [high]": style.PALETTE["blue"],
    "claude-opus-4-7 [thinking]": style.PALETTE["bluish_green"],
    "Gemma 4 31B IT": style.PALETTE["orange"],
    "Tiny-Aya global": style.PALETTE["reddish_purple"],
}


def make_community_profile(df: pd.DataFrame):
    style.apply_style()
    if "is_completed" not in df.columns:
        df = add_derived_columns(df)

    search_models = search_model_set(df)
    completed = df[df.is_completed & ~df.model_display.isin(search_models)]

    acc = (
        completed.groupby(["model_display", "instance_community"])["is_correct"]
        .mean()
        .unstack("instance_community")
        .mul(100)
    )
    # x order: easiest community left
    col_order = acc.mean(axis=0).sort_values(ascending=False).index
    acc = acc[col_order]
    x = range(len(col_order))

    fig, ax = plt.subplots(figsize=(9, 4.8))

    # context: every closed-book model, thin grey
    order = [m for m in model_summary(df).index if m in acc.index]
    for model in order:
        if model in HIGHLIGHTS:
            continue
        ax.plot(x, acc.loc[model], color=style.PALETTE["grey"],
                lw=0.7, alpha=0.35, zorder=1)

    # highlighted models
    for model, color in HIGHLIGHTS.items():
        if model in acc.index:
            ax.plot(x, acc.loc[model], color=color, lw=1.6,
                    label=model, zorder=3)

    # cross-model mean
    ax.plot(x, acc.mean(axis=0), color=style.PALETTE["black"], lw=2.0,
            ls="--", label="mean, all closed-book models", zorder=4)

    ax.set_xticks(list(x), col_order, rotation=60, ha="right", fontsize=6.5)
    ax.set_xlim(-0.5, len(col_order) - 0.5)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Accuracy over completed responses (%)")
    ax.set_title(
        "v0 accuracy profiles across all 44 communities, automatic "
        "evaluation (communities sorted by mean accuracy)"
    )
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="upper right", fontsize=7.5, frameon=True, framealpha=0.9)

    fig.text(
        0.01, 0.005,
        "Grey lines: remaining closed-book models. Search-enabled runs "
        "excluded (separate evaluation category).",
        fontsize=7, color=style.PALETTE["grey"],
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return fig


def main() -> None:
    parquet = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "data/processed/results_tidy.parquet"
    )
    df = pd.read_parquet(parquet)
    fig = make_community_profile(df)
    out = Path("figures/out/community_profile")
    style.save_figure(fig, out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight")
    print(f"Wrote {out}.pdf and {out}.png")


if __name__ == "__main__":
    main()
