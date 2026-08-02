"""Reference-answer heuristic evaluator for framework results.

Run directly from the repository root:

    python evals/reference_heuristic_judge.py framework/runs/examples/5c5b3151-d3a1-4228-9e83-742b4cd2cd58/results.jsonl

Add abstention phrases on the command line or from a UTF-8 file containing one
phrase per line:

    python evals/reference_heuristic_judge.py results.jsonl \
        --additional-no-answer-phrases "I give up" "No clue"
    python evals/reference_heuristic_judge.py results.jsonl \
        --additional-no-answer-phrases-file no_answer_phrases.txt
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ANSWER_KEYS = ("riddle_answer", "answer", "final_answer", "riddleAnswer")
MIN_CONTAINED_CHARS = 4

FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
ANSWER_FIELD_RE = re.compile(
    r"""["']?(?:riddle_answer|answer|final_answer|riddleAnswer)["']?\s*:\s*"""
    r"""(?:"((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)'|([^,\n\r}]+))""",
    re.IGNORECASE | re.DOTALL,
)
PAREN_RE = re.compile(r"\(([^()]*)\)|\uff08([^\uff08\uff09]*)\uff09")
SEPARATOR_RE = re.compile(r"\s*/\s*|[;,\u061b\uff0c\u3001]")
SPACED_HYPHEN_RE = re.compile(r"\s+(?:-|\u2013|\u2014)\s+")

NO_ANSWER_PHRASES_RAW = (
    "I don't know",
    "I do not know",
    "I dont know",
    "Don't know",
    "Do not know",
    "Unknown",
    "Not sure",
    "Unsure",
    "No answer",
    "Cannot answer",
    "Can not answer",
    "我不知道",
    "不知道",
    "لا اعرف",
    "لا ادري",
    "مش عارف",
    "ما اعرف",
    "لا اعلم",
    "не знаю",
    "я не знаю",
    "தெரியாது",
)


@dataclass(frozen=True)
class CandidateParse:
    candidate: str
    status: str
    error: str | None = None


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    match_type: str | None = None
    matched_reference_text: str | None = None
    reason: str = ""


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL row: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object row")
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _extract_answer_from_object(obj: Any) -> str | None:
    if not isinstance(obj, dict):
        return None
    for key in ANSWER_KEYS:
        value = obj.get(key)
        if value is not None:
            return str(value)
    return None


def _json_answer(text: str) -> str | None:
    obj = json.loads(text)
    return _extract_answer_from_object(obj)


def _embedded_json_answer(text: str) -> str | None:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text[match.start() :])
        except json.JSONDecodeError:
            continue
        answer = _extract_answer_from_object(obj)
        if answer is not None:
            return answer
    return None


def _regex_answer(text: str) -> str | None:
    match = ANSWER_FIELD_RE.search(text)
    if not match:
        return None

    value = next(group for group in match.groups() if group is not None)
    value = value.strip().strip("\"'")
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value


def _looks_structured(text: str) -> bool:
    stripped = text.lstrip()
    return (
        stripped.startswith("{")
        or stripped.startswith("[")
        or "```" in text
        or "riddle_answer" in text
        or "final_answer" in text
    )


def parse_candidate(row: dict[str, Any]) -> CandidateParse:
    parsed_json = row.get("parsed_json")
    answer = _extract_answer_from_object(parsed_json)
    if answer is not None:
        return CandidateParse(answer.strip(), "parsed_json")

    if isinstance(parsed_json, str) and parsed_json.strip():
        try:
            answer = _json_answer(parsed_json)
        except json.JSONDecodeError:
            answer = None
        if answer is not None:
            return CandidateParse(answer.strip(), "parsed_json_string")

    raw = str(row.get("raw_response") or "").strip()
    if not raw:
        return CandidateParse("", "parse_error", "raw_response is empty")

    try:
        answer = _json_answer(raw)
    except json.JSONDecodeError:
        answer = None
    if answer is not None:
        return CandidateParse(answer.strip(), "raw_json")

    for fenced in FENCE_RE.findall(raw):
        try:
            answer = _json_answer(fenced.strip())
        except json.JSONDecodeError:
            answer = None
        if answer is not None:
            return CandidateParse(answer.strip(), "fenced_json")

    answer = _embedded_json_answer(raw)
    if answer is not None:
        return CandidateParse(answer.strip(), "embedded_json")

    answer = _regex_answer(raw)
    if answer is not None:
        return CandidateParse(answer.strip(), "regex_key")

    if _looks_structured(raw):
        return CandidateParse("", "parse_error", "could not extract riddle_answer")

    return CandidateParse(raw, "free_text")


def _strip_edge_punctuation(text: str) -> str:
    protected = set("()[]{}\uff08\uff09")
    start = 0
    end = len(text)
    while (
        start < end
        and text[start] not in protected
        and unicodedata.category(text[start])[0] in {"P", "S"}
    ):
        start += 1
    while (
        end > start
        and text[end - 1] not in protected
        and unicodedata.category(text[end - 1])[0] in {"P", "S"}
    ):
        end -= 1
    return text[start:end].strip()


def normalize_text(text: Any) -> str:
    """Apply one conservative normalizer for every language/script."""
    value = unicodedata.normalize("NFKC", str(text or "")).casefold()
    chars: list[str] = []
    for char in value:
        category = unicodedata.category(char)
        if char.isspace():
            continue
        if category[0] not in {"C", "P", "S", "Z"}:
            chars.append(char)
    return "".join(chars)


def _clean_reference_piece(text: str) -> str:
    return _strip_edge_punctuation(re.sub(r"\s+", " ", str(text or "")).strip())


def expand_reference(reference: Any) -> list[str]:
    """Return reference alternatives without adding semantic synonyms."""
    queue = [_clean_reference_piece(str(reference or ""))]
    seen: set[str] = set()
    expanded: list[str] = []

    while queue:
        item = _clean_reference_piece(queue.pop(0))
        if not item or item in seen:
            continue
        seen.add(item)
        expanded.append(item)

        for match in PAREN_RE.finditer(item):
            inner = _clean_reference_piece(match.group(1) or match.group(2) or "")
            if inner and inner not in seen:
                queue.append(inner)

        without_parentheses = _clean_reference_piece(PAREN_RE.sub(" ", item))
        if without_parentheses and without_parentheses not in seen:
            queue.append(without_parentheses)

        for splitter in (SEPARATOR_RE, SPACED_HYPHEN_RE):
            parts = [_clean_reference_piece(part) for part in splitter.split(item)]
            if len(parts) > 1:
                queue.extend(part for part in parts if part and part not in seen)

    return expanded


def _contains_guarded(longer: str, shorter: str) -> bool:
    if not longer or not shorter or longer == shorter:
        return False
    if len(shorter) < MIN_CONTAINED_CHARS:
        return False
    return shorter in longer


def load_no_answer_phrases(path: Path) -> list[str]:
    """Load non-empty abstention phrases from a UTF-8 file, one per line."""
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def is_no_answer(
    candidate: Any,
    *,
    additional_no_answer_phrases: tuple[str, ...] = (),
) -> bool:
    normalized = normalize_text(candidate)
    if not normalized:
        return False
    phrases = (*NO_ANSWER_PHRASES_RAW, *additional_no_answer_phrases)
    return any(
        normalized_phrase and normalized.startswith(normalized_phrase)
        for phrase in phrases
        if (normalized_phrase := normalize_text(phrase))
    )


def match_candidate_to_reference(candidate: Any, reference: Any) -> MatchResult:
    candidate_normalized = normalize_text(candidate)
    reference_alternatives = expand_reference(reference)

    if not candidate_normalized:
        return MatchResult(False, reason="candidate answer is empty after normalization")
    if not reference_alternatives:
        return MatchResult(False, reason="reference answer is empty")

    for reference_text in reference_alternatives:
        reference_normalized = normalize_text(reference_text)
        if candidate_normalized == reference_normalized:
            match_type = "normalized_exact"
            if reference_text != str(reference or "").strip():
                match_type = "reference_alternative_exact"
            return MatchResult(
                True,
                match_type=match_type,
                matched_reference_text=reference_text,
                reason="candidate matched a normalized reference form",
            )

    for reference_text in reference_alternatives:
        reference_normalized = normalize_text(reference_text)
        if _contains_guarded(candidate_normalized, reference_normalized):
            return MatchResult(
                True,
                match_type="candidate_contains_reference",
                matched_reference_text=reference_text,
                reason="candidate contains a sufficiently specific reference form",
            )
        if _contains_guarded(reference_normalized, candidate_normalized):
            return MatchResult(
                True,
                match_type="reference_contains_candidate",
                matched_reference_text=reference_text,
                reason="reference contains the normalized candidate answer",
            )

    return MatchResult(False, reason="candidate did not match any reference form")


def evaluate_row(
    row: dict[str, Any],
    *,
    additional_no_answer_phrases: tuple[str, ...] = (),
) -> dict[str, Any]:
    parsed = parse_candidate(row)
    reference = row.get("reference_answer_original")
    candidate = parsed.candidate

    output = {
        "riddle_id": row.get("riddle_id"),
        "candidate": candidate,
        "reference": reference,
        "match": False,
        "verdict": "incorrect",
        "score": 0,
        "match_type": None,
        "matched_reference_text": None,
        "parse_status": parsed.status,
        "reason": "",
    }

    if parsed.status == "parse_error":
        output["verdict"] = "parse_error"
        output["reason"] = parsed.error or "could not parse candidate answer"
        return output

    if is_no_answer(
        candidate,
        additional_no_answer_phrases=additional_no_answer_phrases,
    ):
        output["verdict"] = "unknown"
        output["score"] = 1
        output["match_type"] = "no_answer"
        output["reason"] = "candidate explicitly says it does not know"
        return output

    match_result = match_candidate_to_reference(candidate, reference)
    output["reason"] = match_result.reason
    if match_result.matched:
        output["match"] = True
        output["verdict"] = "correct"
        output["score"] = 3
        output["match_type"] = match_result.match_type
        output["matched_reference_text"] = match_result.matched_reference_text
    return output


def default_output_dir(results_path: Path, rows: list[dict[str, Any]]) -> Path:
    run_id = next((str(row.get("run_id")) for row in rows if row.get("run_id")), None)
    name = run_id or results_path.stem
    return Path(__file__).resolve().parent / "outputs" / name


def summarize(results: list[dict[str, Any]], *, input_path: Path, output_jsonl: Path) -> dict[str, Any]:
    verdict_counts = Counter(str(row.get("verdict")) for row in results)
    score_counts = Counter(str(row.get("score")) for row in results)
    match_type_counts = Counter(str(row.get("match_type") or "none") for row in results)
    total = len(results)
    matched = sum(1 for row in results if row.get("match"))
    return {
        "input_path": str(input_path),
        "output_jsonl": str(output_jsonl),
        "total": total,
        "matched": matched,
        "match_rate": matched / total if total else 0.0,
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "score_counts": dict(sorted(score_counts.items())),
        "match_type_counts": dict(sorted(match_type_counts.items())),
    }


def evaluate_file(
    results_path: Path,
    *,
    out_dir: Path | None = None,
    out_jsonl: Path | None = None,
    summary_json: Path | None = None,
    limit: int | None = None,
    additional_no_answer_phrases: tuple[str, ...] = (),
) -> tuple[Path, Path, dict[str, Any]]:
    rows = load_jsonl(results_path)
    if limit is not None:
        rows = rows[:limit]

    output_dir = out_dir or default_output_dir(results_path, rows)
    output_jsonl = out_jsonl or output_dir / "heuristic_match.jsonl"
    output_summary = summary_json or output_dir / "heuristic_summary.json"

    evaluated = [
        evaluate_row(
            row,
            additional_no_answer_phrases=additional_no_answer_phrases,
        )
        for row in rows
    ]
    write_jsonl(output_jsonl, evaluated)

    summary = summarize(evaluated, input_path=results_path, output_jsonl=output_jsonl)
    output_summary.parent.mkdir(parents=True, exist_ok=True)
    output_summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_jsonl, output_summary, summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score a framework results.jsonl with reference-answer heuristics.",
    )
    parser.add_argument("results", help="Path to a framework results.jsonl file.")
    parser.add_argument("--out-dir", help="Directory for heuristic_match.jsonl and heuristic_summary.json.")
    parser.add_argument("--out-jsonl", help="Explicit output JSONL path.")
    parser.add_argument("--summary-json", help="Explicit summary JSON path.")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N rows.")
    parser.add_argument(
        "--additional-no-answer-phrases",
        nargs="+",
        action="extend",
        default=[],
        metavar="PHRASE",
        help=(
            "Additional abstention phrases. Quote phrases containing spaces; "
            "the option may be repeated."
        ),
    )
    parser.add_argument(
        "--additional-no-answer-phrases-file",
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "UTF-8 file containing one additional abstention phrase per line; "
            "blank lines are ignored and the option may be repeated."
        ),
    )
    parser.add_argument("--quiet", action="store_true", help="Do not print the summary line.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    results_path = Path(args.results)
    if not results_path.exists():
        parser.error(f"results file not found: {results_path}")

    additional_no_answer_phrases = list(args.additional_no_answer_phrases)
    for phrases_path_arg in args.additional_no_answer_phrases_file:
        phrases_path = Path(phrases_path_arg)
        try:
            additional_no_answer_phrases.extend(load_no_answer_phrases(phrases_path))
        except (OSError, UnicodeError) as exc:
            parser.error(f"could not read no-answer phrases file {phrases_path}: {exc}")

    out_jsonl, summary_json, summary = evaluate_file(
        results_path,
        out_dir=Path(args.out_dir) if args.out_dir else None,
        out_jsonl=Path(args.out_jsonl) if args.out_jsonl else None,
        summary_json=Path(args.summary_json) if args.summary_json else None,
        limit=args.limit,
        additional_no_answer_phrases=tuple(additional_no_answer_phrases),
    )

    if not args.quiet:
        print(
            f"Evaluated {summary['total']} rows: "
            f"{summary['matched']} matched ({summary['match_rate']:.1%})."
        )
        print(f"Wrote {out_jsonl}")
        print(f"Wrote {summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
