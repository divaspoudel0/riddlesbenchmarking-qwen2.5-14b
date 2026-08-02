# Evals

This package scores a benchmark run's `results.jsonl` (the framework's output).
It bundles two complementary evaluators:

- **Reference-answer heuristic evaluator** (`reference_heuristic_judge.py`) — a
  small, deterministic checker. No LLM call. Matches the model's answer against
  the source-language reference answer.
- **LLM-as-a-judge** (`llm_judge_run.py` + `llm_as_a_judge.py`) — lenient LLM
  scoring that credits paraphrases / transliterations the deterministic match
  misses.

## Quick start

Both evaluators take a framework run's `results.jsonl`. Use the committed
example run as a ready-to-use input. Run from the repository root:

```bash
# Deterministic heuristic match (no LLM, no API key)
python evals/reference_heuristic_judge.py \
  framework/runs/examples/5c5b3151-d3a1-4228-9e83-742b4cd2cd58/results.jsonl

# LLM-as-a-judge (needs GEMINI_API_KEY)
python -m evals.llm_judge_run \
  framework/runs/examples/5c5b3151-d3a1-4228-9e83-742b4cd2cd58/results.jsonl \
  --model gemini-2.5-flash-lite
```

See the per-evaluator sections below for inputs, outputs, and options.

---

# Reference-Answer Heuristic Evaluator

This script reads model outputs from a `results.jsonl` file, extracts the
model's answer, compares it with the source-language reference answer, and
writes a per-riddle score file plus a short summary. It does not call an LLM.

Run it from the repository root:

```bash
python evals/reference_heuristic_judge.py \
  framework/runs/examples/5c5b3151-d3a1-4228-9e83-742b4cd2cd58/results.jsonl
```

To extend the built-in abstention phrases for a run, supply phrases directly
or load them from a UTF-8 file:

```bash
# Supply a list
python evals/reference_heuristic_judge.py results.jsonl \
  --additional-no-answer-phrases "I give up" "No clue"

# Supply a UTF-8 file, one phrase per line
python evals/reference_heuristic_judge.py results.jsonl \
  --additional-no-answer-phrases-file phrases.txt
```

By default, the files are written here:

```text
evals/outputs/<run_id_or_input_stem>/
  heuristic_match.jsonl
  heuristic_summary.json
```

## Model Input And Answer Format

This evaluator does not build prompts or run models. When you prepare the model
run, the only mandatory input the model needs is the riddle text. Do not put
the reference answer in the prompt.

The model answer should be a JSON object with this mandatory field:

```json
{
  "riddle_answer": "the model's answer"
}
```

If the model also returns `reasoning`, this evaluator ignores it.

## Results File Input

The script expects a JSONL file where each line is one model result.

Mandatory fields:

- `raw_response`: the model's raw answer text.
- `reference_answer_original`: the correct answer in the original/source language.

Recommended but not required:

- `riddle_id`: copied into the output so rows are easy to trace.
- `run_id`: used to name the default output folder.
- `parsed_json`: used first if it already contains the parsed model answer.

If the model returns plain text, the script treats that whole text as the
answer. If the model returns broken structured text and no answer can be
extracted, the row is marked as a parse error.

Only `reference_answer_original` is used for matching. `reference_answer_english`
is ignored.

## Output

`heuristic_match.jsonl` contains one JSON object per result row:

```json
{
  "riddle_id": "example_id",
  "candidate": "model answer",
  "reference": "reference answer",
  "match": true,
  "verdict": "correct",
  "score": 3,
  "match_type": "normalized_exact",
  "matched_reference_text": "reference answer",
  "parse_status": "raw_json",
  "reason": "candidate matched a normalized reference form"
}
```

Scores are intentionally simple:

- `3`: the model answer matched the reference by a deterministic rule.
- `1`: the model explicitly said it did not know.
- `0`: the model answer did not match, or the answer could not be parsed.

`heuristic_summary.json` reports totals, match rate, verdict counts, score
counts, and match-type counts.

## Matching Rules

The normalizer is intentionally shared across all languages:

- Unicode-normalize text with `NFKC`.
- Lowercase with Python's `casefold()`.
- Remove whitespace.
- Remove punctuation, symbols, separators, and control characters.
- Keep letters, numbers, and script marks as they are.

The script also expands reference answers written as simple alternatives, such
as `answer one / answer two`, `answer (alias)`, comma-separated lists,
semicolon-separated lists, and spaced hyphen pairs.

It does not translate, transliterate, stem words, guess synonyms, or use
language-specific cleanup. That keeps the behavior predictable across large
multilingual runs.

## Useful Options

```bash
python evals/reference_heuristic_judge.py results.jsonl --out-dir evals/outputs/my_run
python evals/reference_heuristic_judge.py results.jsonl --limit 100
python evals/reference_heuristic_judge.py results.jsonl --quiet
```

---

# LLM-as-a-judge

Lenient LLM scoring of the same `results.jsonl` (credits paraphrases /
transliterations that exact match misses). Reuses the judge prompt + output
schema from `llm_as_a_judge.py`; sends via Google's OpenAI-compatible Gemini
endpoint with `gemini-2.5-flash-lite` by default. Needs `GEMINI_API_KEY`:

```bash
python -m evals.llm_judge_run \
  framework/runs/examples/5c5b3151-d3a1-4228-9e83-742b4cd2cd58/results.jsonl \
  --model gemini-2.5-flash-lite
```

Writes verdicts (same shape as the heuristic match) to `<run_dir>/llm_judge.jsonl`.
