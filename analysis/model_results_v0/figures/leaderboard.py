"""Figure 1: v0 automatic-evaluation leaderboard (Cleveland dot plot).

Pure function `make_leaderboard(df) -> fig`, plus a CLI that saves PDF (paper)
and PNG (slides/blog). Import the function in the notebook to render inline.

    from figures.leaderboard import make_leaderboard
    fig = make_leaderboard(df)
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# Put analysis/ (for style.py) and model_results_v0/ (for metrics.py) on path.
_HERE = Path(__file__).resolve()
sys.path.append(str(_HERE.parents[2]))  # analysis/
sys.path.append(str(_HERE.parents[1]))  # analysis/model_results_v0/
import style  # noqa: E402
from metrics import (  # noqa: E402
    SEARCH_NOTE,
    add_derived_columns,
    label_with_search,
    model_summary_with_ci,
    search_model_set,
)

FLOOR_THRESHOLD = 0.05  # format-failure rate above which a score is a floor


def make_leaderboard(df: pd.DataFrame, n_boot: int = 2000):
    """Cleveland dot plot of accuracy over completed responses, with 95% CIs.

    Annotates reduced denominators (n=...) and marks token-truncation floors (*).
    """
    style.apply_style()
    if "is_completed" not in df.columns:
        df = add_derived_columns(df)

    lb = model_summary_with_ci(df, n_boot=n_boot).iloc[::-1]  # worst at bottom
    search_models = search_model_set(df)
    # Full run size = riddles attempted (auto-adjusts if any riddle is
    # excluded, e.g. a corrected riddle), so full-coverage models are not
    # falsely annotated with a reduced denominator.
    full_n = int(lb.n_total.max())

    labels = []
    for model, n, ffr in zip(lb.index, lb.n_completed, lb.format_failure_rate):
        label = label_with_search(model, search_models)
        if n < full_n:
            label += f" (n={int(n):,})"
        if ffr >= FLOOR_THRESHOLD:
            label += " *"
        labels.append(label)

    fig, ax = plt.subplots(figsize=(7.5, 8))
    y = list(range(len(lb)))
    ax.hlines(y, lb.ci_low * 100, lb.ci_high * 100,
              color=style.PALETTE["grey"], lw=1.5, zorder=1)
    # Search-enabled runs sit in the same ranking as everything else; they
    # are distinguished only by the "(search)" label, not a separate marker.
    ax.plot(lb.accuracy * 100, y, "o", color=style.PALETTE["blue"],
            markersize=6, zorder=2)

    ax.set_yticks(y, labels)
    ax.set_ylim(-0.5, len(lb) - 0.5)
    ax.set_xlabel("Accuracy over completed responses (%), heuristic judge")
    ax.set_title("v0 leaderboard, automatic evaluation")
    ax.grid(axis="x", alpha=0.3)
    ax.grid(axis="y", visible=False)

    footnote = (
        f"(n=...) = completed responses, shown where below {full_n:,}.   "
        "* = floor: >=5% of responses hit the token budget before answering."
    )
    if search_models:
        footnote += "\n" + SEARCH_NOTE
    fig.text(0.01, 0.005, footnote,
             fontsize=7, color=style.PALETTE["grey"])
    fig.tight_layout(rect=(0, 0.045 if search_models else 0.03, 1, 1))
    return fig


def main() -> None:
    parquet = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "data/processed/results_tidy.parquet"
    )
    df = pd.read_parquet(parquet)
    fig = make_leaderboard(df)
    out = Path("figures/out/leaderboard")
    style.save_figure(fig, out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight")
    print(f"Wrote {out}.pdf and {out}.png")


if __name__ == "__main__":
    main()
