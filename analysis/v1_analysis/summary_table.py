from __future__ import annotations

import pandas as pd

from text_features import CSV_DIR, display_label

HINT_FULL_THRESHOLD = 0.9
HINT_NONE_THRESHOLD = 0.05


def hint_bucket(fill_rate: float) -> str:
    if fill_rate >= HINT_FULL_THRESHOLD:
        return "full"
    if fill_rate <= HINT_NONE_THRESHOLD:
        return "none"
    return "partial"


def build_hint_coverage(consolidated: pd.DataFrame) -> pd.DataFrame:
    coverage = consolidated.groupby("community")["riddle_hint"].apply(lambda s: s.notna().mean())
    coverage = coverage.rename("hint_fill_rate").reset_index()
    coverage["hint_bucket"] = coverage["hint_fill_rate"].map(hint_bucket)
    return coverage


def main() -> None:
    consolidated = pd.read_csv(CSV_DIR / "riddles_v1_consolidated.csv")
    form_length = pd.read_csv(CSV_DIR / "riddle_form_length_per_culture.csv")
    answers = pd.read_csv(CSV_DIR / "answer_diversity_per_culture.csv")
    lexical = pd.read_csv(CSV_DIR / "lexical_diversity_per_culture.csv")
    validators = pd.read_csv(CSV_DIR / "validator_coverage_per_culture.csv")
    hints = build_hint_coverage(consolidated)

    summary = form_length[
        ["community", "display_label", "n_riddles", "mean_word_count", "cv_word_count", "frac_question", "frac_first_person", "frac_multiline"]
    ]
    summary = summary.merge(
        answers[["community", "answer_fill_rate", "unique_answer_ratio_of_filled", "entity_like_ratio"]],
        on="community",
        how="left",
    )
    summary = summary.merge(
        lexical[["community", "root_ttr", "rare_token_fraction", "hapax_ratio"]], on="community", how="left"
    )
    summary = summary.merge(hints[["community", "hint_fill_rate", "hint_bucket"]], on="community", how="left")
    summary = summary.merge(
        validators[["community", "validator_coverage", "n_rated", "pct_correct_of_rated"]],
        on="community",
        how="left",
    )

    summary = summary.sort_values("display_label").reset_index(drop=True)
    summary.to_csv(CSV_DIR / "per_culture_master_summary.csv", index=False)

    print(f"cultures: {len(summary)}")
    print(f"total riddles: {summary['n_riddles'].sum()}")
    print(f"hint buckets: {hints['hint_bucket'].value_counts().to_dict()}")
    print(summary.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
