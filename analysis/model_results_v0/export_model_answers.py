"""Export the tier-2 HuggingFace artifact: model answers parquet.

Produces model_answers.parquet from the tidy frame: one row per
(riddle_id, model), with the extracted answer, generation status, and
automatic judge scores. Excludes raw metadata not meant for release
(cache config, provider internals) and keeps column names aligned with
Henry's human-eval metadata (riddle_id, answer_text) so the tier-3
human_annotations config can join cleanly.

Field definitions (for the dataset card):

- riddle_id            riddle identifier ({community}_{topic}_{n})
- community            community slug (44 values in v0)
- language             ISO code of the riddle language
- condition_id         benchmark condition (v0: source_no_hint only)
- model_name           model name as configured by the runner
- model_id             provider-qualified model identifier
- reasoning_mode       reasoning setting ("none" if not applicable)
- model_display        disambiguated display name used in figures
- eval_category        closed_book | search_enabled; search-enabled runs are
                       a separate category, not comparable to closed-book
- answer_text          answer extracted from the model response (null if none)
- answer_parse_status  json | regex | regex_single_quote | unparsed | empty
- generation_status    runner status (success / error)
- output_tokens        tokens generated (truncation diagnostics)
- judge_score          heuristic judge score (0/1/3)
- judge_verdict        correct | incorrect | unknown | parse_error
- judge_match_type     heuristic match category

Usage:
    python export_model_answers.py [parquet_in] [parquet_out]
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

EXPORT_COLUMNS = [
    "riddle_id",
    "instance_community",
    "instance_language",
    "condition_id",
    "model_name",
    "model_id",
    "reasoning_mode",
    "model_display",
    "eval_category",
    "answer_text",
    "answer_parse_status",
    "generation_status",
    "output_tokens",
    "judge_score",
    "judge_verdict",
    "judge_match_type",
]

RENAME = {
    "instance_community": "community",
    "instance_language": "language",
}


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "data/processed/results_tidy.parquet"
    )
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
        "data/processed/model_answers.parquet"
    )
    df = pd.read_parquet(src)
    export = df[EXPORT_COLUMNS].rename(columns=RENAME)
    out.parent.mkdir(parents=True, exist_ok=True)
    export.to_parquet(out, index=False)
    print(f"Wrote {out}: {len(export):,} rows, {len(export.columns)} columns")
    print(f"  models: {export.model_display.nunique()}, "
          f"communities: {export.community.nunique()}")


if __name__ == "__main__":
    main()
