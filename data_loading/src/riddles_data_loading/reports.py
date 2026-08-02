"""Report generation helpers."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def summarize_result(file_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    """Return one compact CSV-friendly summary row for a workbook result."""

    insights = result.get("insights", {})
    primary_answer_check = _primary_answer_check(insights)
    blocking_issues = result.get("blocking_issues", [])
    tolerated_issues = result.get("tolerated_issues", [])
    return {
        "file": str(file_path),
        "passed": bool(result["passed"]),
        "blocking_issue_count": len(result.get("blocking_issues", [])),
        "failure_reason": blocking_issues[0] if blocking_issues else "",
        "blocking_issues": _join_issues(blocking_issues),
        "tolerated_issue_count": len(result.get("tolerated_issues", [])),
        "tolerated_issues": _join_issues(tolerated_issues),
        "expected_row_count": insights.get("expected_row_count"),
        "query_row_count": insights.get("query_row_count"),
        "query_row_count_matches_expected": insights.get(
            "query_row_count_matches_expected"
        ),
        "loaded_sheet_name": insights.get("loaded_sheet_name"),
        "used_sheet_fallback": insights.get("used_sheet_fallback", False),
        "missing_answer_count": primary_answer_check.get("missing_count"),
        "duplicate_answer_group_count": primary_answer_check.get(
            "duplicate_group_count"
        ),
        "duplicate_answer_row_count": primary_answer_check.get("duplicate_row_count"),
        "query_topic_count_issue_count": len(
            insights.get("query_topic_count_issues", [])
        ),
        "wildcard_replacement_topics": _join_issues(
            insights.get("wildcard_replacement_topics", [])
        ),
        "wildcard_1_new_topic": insights.get("wildcard_1_new_topic"),
        "wildcard_2_new_topic": insights.get("wildcard_2_new_topic"),
        "jsonl_path": insights.get("jsonl_path"),
        "passed_jsonl_path": insights.get("passed_jsonl_path"),
    }


def write_reports(
    results: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    output_dir: Path,
) -> tuple[Path, Path]:
    """Write full JSON results and a compact CSV summary."""

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "validation_summary.csv"
    json_path = output_dir / "validation_results.json"

    pd.DataFrame(summary_rows).to_csv(csv_path, index=False)
    json_path.write_text(
        json.dumps(_json_safe(results), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return csv_path, json_path


def write_submission_jsonl(
    dataframe: pd.DataFrame,
    source_path: Path,
    sheet_name: str,
    output_dir: Path,
) -> Path:
    """Export one submitted workbook sheet as line-delimited JSON."""

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{_safe_jsonl_stem(source_path)}.jsonl"

    with output_path.open("w", encoding="utf-8") as handle:
        for row_index, row in dataframe.iterrows():
            record = {
                "_source_file": source_path.name,
                "_source_sheet": sheet_name,
                "_row_index": int(row_index) if isinstance(row_index, int) else row_index,
                **row.to_dict(),
            }
            handle.write(json.dumps(_json_safe(record), ensure_ascii=False))
            handle.write("\n")

    return output_path


def _primary_answer_check(insights: dict[str, Any]) -> dict[str, Any]:
    answer_checks = insights.get("answer_checks", {})
    if not answer_checks:
        return {}
    if "Reference Answer (Original)" in answer_checks:
        return answer_checks["Reference Answer (Original)"]
    return next(iter(answer_checks.values()))


def _join_issues(issues: list[object]) -> str:
    return " | ".join(str(issue) for issue in issues)


def _safe_jsonl_stem(path: Path) -> str:
    stem = path.stem.casefold()
    stem = re.sub(r"[^a-z0-9]+", "_", stem)
    stem = stem.strip("_")
    return stem or "submission"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(_json_safe(key)): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        if math.isnan(float(value)):
            return None
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float) and math.isnan(value):
        return None
    if value is pd.NA or value is pd.NaT:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    except ValueError:
        pass
    if hasattr(value, "item"):
        return _json_safe(value.item())
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if value is None:
        return None
    return value
