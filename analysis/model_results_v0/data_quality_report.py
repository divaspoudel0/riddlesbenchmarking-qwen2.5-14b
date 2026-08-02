"""Generate a data quality report for a results version.

Reads the tidy parquet produced by load_results.py and writes a markdown
report covering response health per model: parse status, empty responses,
token-limit truncations, and judge verdict distribution.

Rerun on each dataset version (v0, v1, ...) to keep a comparable record of
run quality over time.

Usage:
    python data_quality_report.py [parquet_path] [out_md] [version_label]
    defaults: data/processed/results_tidy.parquet  DATA_QUALITY_v0.md  v0
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

TRUNCATION_TOKENS = 4000  # near the shared 4096 max_output_tokens budget


def build_report(df: pd.DataFrame, version: str) -> str:
    lines = [
        f"# Data quality report: {version} model runs",
        "",
        f"Generated {date.today().isoformat()} by data_quality_report.py. "
        "Do not edit by hand; rerun the script.",
        "",
        f"Rows: {len(df)}, models: {df['model_display'].nunique()}, "
        f"communities: {df['instance_community'].nunique()}, "
        f"conditions: {df['condition_id'].nunique()}",
        "",
        "## Per-model response health",
        "",
        "unparsed = response present but no answer extractable "
        "(mostly reasoning that never reaches the JSON answer). "
        f"truncated = unparsed with >= {TRUNCATION_TOKENS} output tokens, "
        "i.e. the model hit the shared token budget before answering.",
        "",
        "| model | rows | empty | unparsed | truncated | judge correct | judge unknown |",
        "|---|---|---|---|---|---|---|",
    ]

    has_judge = "judge_verdict" in df.columns
    has_category = "eval_category" in df.columns
    for model, g in df.groupby("model_display"):
        empty = (g.answer_parse_status == "empty").sum()
        unparsed = g.answer_parse_status == "unparsed"
        truncated = (
            unparsed & (g.output_tokens.fillna(0) >= TRUNCATION_TOKENS)
        ).sum()
        correct = (g.judge_verdict == "correct").sum() if has_judge else "-"
        unknown = (g.judge_verdict == "unknown").sum() if has_judge else "-"
        label = model
        if has_category and g.eval_category.iloc[0] == "search_enabled":
            label = f"{model} (search-enabled, separate category)"
        lines.append(
            f"| {label} | {len(g)} | {empty} | {unparsed.sum()} | "
            f"{truncated} | {correct} | {unknown} |"
        )

    lines += [
        "",
        "## Notable findings",
        "",
        "Threshold: models with more than 5% of rows empty or unparsed.",
        "",
    ]
    for model, g in df.groupby("model_display"):
        bad = g.answer_parse_status.isin(["empty", "unparsed"]).mean()
        if bad > 0.05:
            unparsed = g.answer_parse_status == "unparsed"
            truncated = (
                unparsed & (g.output_tokens.fillna(0) >= TRUNCATION_TOKENS)
            ).sum()
            lines.append(
                f"- {model}: {bad:.1%} of rows have no extractable answer "
                f"({truncated} of {unparsed.sum()} unparsed rows hit the "
                "token budget)."
            )

    lines += [
        "",
        "## Version notes (hand-maintained context, append per version)",
        "",
        "- v0: Command A+ July 13 rerun fixed earlier empty responses (404s) "
        "but 1,122 of its 1,136 unparsed rows hit the 4,096 token budget "
        "mid-reasoning; kept as-is for v0, scored as format failures, "
        "flagged to leads 15 Jul 2026.",
        "- v0: Amazon Nova Micro emits pseudo-JSON with single-quoted values; "
        "handled in load_results.extract_answer.",
        "- v0: Qwen-SEA-LION and OLMo-3-32B-Think spill reasoning and "
        "truncate before answering on a subset of rows; treated as genuine "
        "no-answers.",
        "- v0: judge abstention detection (NO_ANSWER_PHRASES_RAW) covers ~6 of "
        "30+ benchmark languages; honest-uncertainty rates are lower bounds. "
        "Raised with Abdellah 19 Jul 2026; rerun scoring once the phrase list "
        "is extended.",
        "- v0: follow-up audit (22 Jul 2026) found zero non-English abstention "
        "phrases in v0 responses. Models abstain in English even when riddles "
        "are presented in other languages, so the language-coverage caveat "
        "above is softer than first feared: English-only detection appears to "
        "capture v0 abstentions in practice.",
        "- v0: 639 answers are literal prompt-template echoes "
        "(530 `<your_riddle_answer>`, 25 `<answer>`, 84 `...`), concentrated "
        "in three runs: OLMo-3-32B-Think (519), Qwen-SEA-LION-v4.5-27B-IT "
        "(88), Command A+ (32). 635 scored incorrect, 4 leaked through as "
        "correct. These are format failures, not knowledge failures; because "
        "they cluster in two or three runs they depress those models' "
        "leaderboard rows specifically. Now reclassified analysis-side "
        "(metrics.TEMPLATE_ECHO_ANSWERS): counted as format failures, never "
        "correct, so they move out of the 'incorrect' bucket and flag the "
        "three runs as format-failure floors. Accuracy is essentially "
        "unchanged (only 4 coincidental matches removed). A judge-side "
        "placeholder reject would supersede this.",
        "- v0: GPT5.5-search (03_gpt-5.5-search, added 22 Jul 2026) ran with "
        "web search enabled. It is a SEPARATE evaluation category "
        "(eval_category=search_enabled in the tidy frame): open-web "
        "retrieval is not comparable to closed-book recall, so figures mark "
        "it with a distinct marker and a '(search)' label suffix. "
        "Clean run (4,400/4,400 parsed JSON), 49.7% raw match, below both "
        "closed-book GPT5.5 variants; flag to leads.",
        "- v0: riddle spanish_cuba_history_016 is excluded from analysis "
        "(EXCLUDED_RIDDLES in load_results). The v0 text was wrong; the "
        "contributor corrected the source row and it is re-evaluated fresh "
        "in v2. Every model's answers to it are answers to the wrong riddle, "
        "so they are dropped from scoring. Denominators are 4,399 riddles "
        "for Spanish (Cuba); the frozen run files are untouched. See "
        "RIDDLE_CORRECTIONS.md (flagged 23 Jul 2026).",
        "- v0: 4 Apertus runs (swiss-ai, folders 30-33) added 31 Jul 2026 "
        "by Hannah: Apertus 8B and 70B in v1 (Instruct-2509) and v1.5. "
        "Closed-book, full v0 coverage (4,400 riddles each, ~all success). "
        "Accuracy 5.6% (v1 8B) to 14.6% (v1.5 70B); v1.5 > v1 and 70B > 8B. "
        "Leaderboard now 29 runs; top unchanged.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parquet = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "data/processed/results_tidy.parquet"
    )
    out_md = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("DATA_QUALITY_v0.md")
    version = sys.argv[3] if len(sys.argv) > 3 else "v0"

    df = pd.read_parquet(parquet)
    out_md.write_text(build_report(df, version), encoding="utf-8")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()
