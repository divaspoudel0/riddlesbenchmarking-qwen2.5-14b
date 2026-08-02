"""Figure 4: response outcome breakdown per model (automatic eval).

100% stacked horizontal bars over completed responses, four outcomes:

- correct              (judge verdict correct)
- honest uncertainty   (explicit "I don't know", judge verdict unknown)
- format failure       (response present, no extractable answer; mostly
                        reasoning truncated at the token budget)
- incorrect            (everything else: a wrong answer, confidently given)

This is the automatic-eval precursor of the hallucination vs honest
uncertainty figure: human eval error types (e.g. 0.3 hallucination) will
refine "incorrect" into subcategories after the sheets complete.
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
    SEARCH_NOTE,
    add_derived_columns,
    label_with_search,
    model_summary,
    search_model_set,
)

OUTCOMES = ["correct", "honest_uncertainty", "format_failure", "incorrect"]
OUTCOME_LABELS = {
    "correct": "Correct",
    "honest_uncertainty": "Honest uncertainty (\u201cI don't know\u201d)",
    "format_failure": "Format failure (no extractable answer)",
    "incorrect": "Incorrect",
}
OUTCOME_COLORS = {
    "correct": style.PALETTE["bluish_green"],
    "honest_uncertainty": style.PALETTE["sky_blue"],
    "format_failure": style.PALETTE["orange"],
    "incorrect": style.PALETTE["vermillion"],
}


def outcome_shares(df: pd.DataFrame) -> pd.DataFrame:
    """Per-model outcome shares over completed responses (rows sum to 1)."""
    completed = df[df.is_completed].copy()
    completed["outcome"] = "incorrect"
    completed.loc[completed.is_format_failure, "outcome"] = "format_failure"
    completed.loc[completed.is_abstention, "outcome"] = "honest_uncertainty"
    completed.loc[completed.is_correct, "outcome"] = "correct"

    shares = (
        completed.groupby("model_display")["outcome"]
        .value_counts(normalize=True)
        .unstack(fill_value=0.0)
        .reindex(columns=OUTCOMES, fill_value=0.0)
    )
    order = model_summary(df).index
    return shares.loc[[m for m in order if m in shares.index]]


def make_failure_modes(df: pd.DataFrame):
    style.apply_style()
    if "is_completed" not in df.columns:
        df = add_derived_columns(df)

    shares = outcome_shares(df).iloc[::-1]  # best model on top
    search_models = search_model_set(df)
    shares.index = [label_with_search(m, search_models) for m in shares.index]

    fig, ax = plt.subplots(figsize=(7.5, 8))
    left = pd.Series(0.0, index=shares.index)
    for outcome in OUTCOMES:
        vals = shares[outcome] * 100
        ax.barh(shares.index, vals, left=left * 100,
                color=OUTCOME_COLORS[outcome],
                label=OUTCOME_LABELS[outcome], height=0.72)
        left = left + shares[outcome]

    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of completed responses (%)")
    ax.set_title("v0 response outcomes by model, automatic evaluation")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", framealpha=0.9, frameon=True, fontsize=7.5)
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
    fig = make_failure_modes(df)
    out = Path("figures/out/failure_modes")
    style.save_figure(fig, out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight")
    print(f"Wrote {out}.pdf and {out}.png")


if __name__ == "__main__":
    main()
