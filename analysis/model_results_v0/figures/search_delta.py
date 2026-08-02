"""Figure: GPT5.5 web search vs closed-book, accuracy delta by community.

Compares the search-enabled GPT5.5 run against its closed-book counterpart
(same no-reasoning config) per community, over completed responses. A
diverging bar chart: communities where search helped on the right, hurt on
the left. Evidence for the "is search actually retrieving anything useful
here" question: if search worked, gains should concentrate in communities
whose riddle answers are documented on the searchable web.

Pure function `make_search_delta(df) -> fig` plus CLI saving PDF + PNG.
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
from metrics import SEARCH_NOTE, add_derived_columns  # noqa: E402

SEARCH_MODEL = "GPT5.5-search"
BASELINE_MODEL = "GPT5.5 [none]"  # same provider config, no reasoning, no search


def make_search_delta(
    df: pd.DataFrame,
    search_model: str = SEARCH_MODEL,
    baseline_model: str = BASELINE_MODEL,
):
    style.apply_style()
    if "is_completed" not in df.columns:
        df = add_derived_columns(df)

    completed = df[df.is_completed & df.model_display.isin(
        [search_model, baseline_model]
    )]
    acc = (
        completed.groupby(["instance_community", "model_display"])["is_correct"]
        .mean()
        .unstack("model_display")
        .mul(100)
    )
    delta = (acc[search_model] - acc[baseline_model]).sort_values()

    overall = (
        completed.groupby("model_display")["is_correct"].mean().mul(100)
    )
    overall_delta = overall[search_model] - overall[baseline_model]

    fig, ax = plt.subplots(figsize=(7, 8.5))
    colors = [
        style.PALETTE["bluish_green"] if v > 0 else style.PALETTE["vermillion"]
        for v in delta
    ]
    ax.barh(delta.index, delta, color=colors, height=0.72)
    ax.axvline(0, color=style.PALETTE["black"], lw=0.8)
    ax.axvline(overall_delta, color=style.PALETTE["grey"], lw=1.0, ls="--")
    ax.text(overall_delta, len(delta) - 0.2,
            f" overall {overall_delta:+.1f}", fontsize=7.5,
            color=style.PALETTE["grey"], va="top",
            ha="left" if overall_delta >= 0 else "right")

    ax.set_yticks(range(len(delta)), delta.index, fontsize=7)
    ax.set_xlabel(
        "Accuracy delta, search minus closed-book (percentage points)"
    )
    ax.set_title(
        f"{search_model} vs {baseline_model}: accuracy delta by community"
    )
    ax.grid(axis="x", alpha=0.3)
    ax.grid(axis="y", visible=False)

    fig.text(
        0.01, 0.005,
        SEARCH_NOTE + "\nBaseline: same GPT5.5 config without search. "
        "Accuracy over completed responses, heuristic judge.",
        fontsize=7, color=style.PALETTE["grey"],
    )
    fig.tight_layout(rect=(0, 0.045, 1, 1))
    return fig


def main() -> None:
    parquet = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "data/processed/results_tidy.parquet"
    )
    df = pd.read_parquet(parquet)
    fig = make_search_delta(df)
    out = Path("figures/out/search_delta")
    style.save_figure(fig, out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight")
    print(f"Wrote {out}.pdf and {out}.png")


if __name__ == "__main__":
    main()
