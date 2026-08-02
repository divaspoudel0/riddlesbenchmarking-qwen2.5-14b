"""Run an LLM judge over a framework run's results.jsonl.

Reuses the provider-agnostic pieces of ``llm_as_a_judge`` (the judge system
prompt, the output schema, and the message builder) but sends the request
through Google's OpenAI-compatible Gemini endpoint with a small Flash-Lite
model by default — so it can run with a ``GEMINI_API_KEY``.

    python -m evals.llm_judge_run framework/runs/examples/<run_id>/results.jsonl
    python -m evals.llm_judge_run <results.jsonl> --model gemini-2.5-flash-lite --limit 5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from evals.llm_as_a_judge import (
    JUDGE_OUTPUT_SCHEMA,
    build_judge_messages,
)

DEFAULT_MODEL = "gemini-2.5-flash-lite"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def candidate_answer(row) -> str:
    """Pull `riddle_answer` out of a framework results row."""
    raw = row.get("raw_response") or ""
    try:
        return str(json.loads(raw).get("riddle_answer", "") or "")
    except Exception:
        return str(raw)


def riddle_from_row(row) -> str:
    """Recover the riddle text from a results row.

    results.jsonl has no `riddle_original` field; the riddle lives inside the
    rendered prompt (`model_input`), placed after a `RIDDLE:` marker by the
    framework. Fall back to the whole prompt if the marker is absent.
    """
    model_input = str(row.get("model_input") or "")
    marker = "RIDDLE:"
    if marker in model_input:
        return model_input.rsplit(marker, 1)[1].strip()
    return model_input.strip()


def judge_instance(row) -> dict:
    """Build the minimal instance dict that build_judge_messages expects."""
    return {
        "riddle_original": riddle_from_row(row),
        "hint": None,
        "reference_answer_original": row.get("reference_answer_original"),
    }


def parse_verdict(content: str) -> dict:
    """Parse the judge's JSON reply into a verdict dict (defensive)."""
    try:
        obj = json.loads(content)
        if isinstance(obj, dict):
            return obj
    except (ValueError, TypeError):
        pass
    return {
        "verdict": "unclear",
        "score": 0,
        "matched_reference": False,
        "reason": f"Unparseable judge reply: {content[:200]!r}",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="LLM judge over a run's results.jsonl (Gemini Flash-Lite)")
    parser.add_argument("results", help="Path to a framework run's results.jsonl")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model (default: {DEFAULT_MODEL})")
    parser.add_argument("--limit", type=int, default=None, help="Judge only the first N rows")
    parser.add_argument("--max-output-tokens", type=int, default=2048,
                        help="Token budget (reasoning models need headroom)")
    parser.add_argument("--out", default=None, help="Output path (default: <run_dir>/llm_judge.jsonl)")
    args = parser.parse_args(argv)

    results_path = Path(args.results)
    if not results_path.exists():
        parser.error(f"results file not found: {results_path}")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        parser.error("GEMINI_API_KEY is not set")

    from openai import OpenAI  # imported here so --help works without the SDK
    client = OpenAI(api_key=api_key, base_url=GEMINI_BASE_URL)

    rows = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.limit is not None:
        rows = rows[: args.limit]

    out_path = Path(args.out) if args.out else results_path.parent / "llm_judge.jsonl"
    correct = 0
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            cand = candidate_answer(row)
            ref = row.get("reference_answer_original")
            messages = build_judge_messages(judge_instance(row), candidate_answer=cand)
            try:
                resp = client.chat.completions.create(
                    model=args.model,
                    messages=messages,
                    max_tokens=args.max_output_tokens,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "judge_result",
                            "strict": True,
                            "schema": JUDGE_OUTPUT_SCHEMA,
                        },
                    },
                )
                content = resp.choices[0].message.content or ""
                verdict = parse_verdict(content)
            except Exception as exc:  # noqa: BLE001
                verdict = {
                    "verdict": "unclear",
                    "score": 0,
                    "matched_reference": False,
                    "reason": f"judge call failed: {exc}",
                }

            correct += bool(verdict.get("matched_reference"))
            f.write(json.dumps(
                {"riddle_id": row.get("riddle_id"), "candidate": cand, "reference": ref, "verdict": verdict},
                ensure_ascii=False,
            ) + "\n")
            mark = "✓" if verdict.get("matched_reference") else "✗"
            print(f"{mark} {row.get('riddle_id')}: {cand!r} vs {ref!r}  [{verdict.get('verdict')}]")

    print(f"\n{correct}/{len(rows)} judged correct ({args.model})  ->  {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
