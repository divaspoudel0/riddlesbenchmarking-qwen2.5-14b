"""Generate a human-readable contributor feedback report.

The default validation_summary.csv is machine-friendly. This module produces
contributor_feedback.csv, which translates blocking issues into plain-English
actions a contributor can read and act on directly.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd


SUBMISSION_NAME_PATTERN = re.compile(r"\[([^\]]+)\]")


def write_contributor_feedback(
    summary_rows: list[dict[str, Any]],
    output_dir: Path,
) -> Path:
    """Write a contributor-friendly feedback CSV alongside validation_summary.csv."""

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "contributor_feedback.csv"

    rows = [_format_row(row) for row in summary_rows]
    rows.sort(key=lambda r: (r["Status"] != "FAILED", r["Submission"]))

    pd.DataFrame(rows).to_csv(output_path, index=False)
    return output_path


def _format_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        "Submission": _submission_name(row.get("file", "")),
        "Status": "PASSED" if row.get("passed") else "FAILED",
        "What to fix (blocking)": _plain_english_action(row) if not row.get("passed") else "",
        "Additional notes (non-blocking)": _tolerated_notes(row),
        "Raw failure reason": row.get("failure_reason", ""),
        "Row count": row.get("query_row_count", ""),
    }


def _submission_name(file_path: str) -> str:
    match = SUBMISSION_NAME_PATTERN.search(file_path)
    if match:
        return match.group(1).strip()
    return Path(file_path).name


def _plain_english_action(row: dict[str, Any]) -> str:
    issues = row.get("blocking_issues", "") or ""
    actions: list[str] = []

    actions.extend(_required_column_actions(issues))
    actions.extend(_topic_count_actions(issues))
    actions.extend(_missing_columns_actions(issues))

    if not actions:
        actions.append(f"See blocking_issues column for detail: {issues}")

    return " | ".join(actions)


def _required_column_actions(issues: str) -> list[str]:
    actions = []
    column_phrasing = {
        "Author": "Author",
        "Topic": "Topic",
        "Reference Answer (Original)": "Reference Answer (Original)",
        "Riddle (Original Language)": "Riddle (Original Language)",
    }

    for column, label in column_phrasing.items():
        escaped = re.escape(column)
        match = re.search(rf"Required column '{escaped}' has (\d+) missing", issues)
        if not match:
            continue
        count = match.group(1)
        if count == "100":
            actions.append(
                f"The '{label}' column is completely empty — please fill it in on every row."
            )
        else:
            actions.append(
                f"Fill in the missing '{label}' value(s) — {count} row(s) are blank."
            )

    return actions


def _topic_count_actions(issues: str) -> list[str]:
    if "topic counts must be exactly 10" not in issues:
        return []
    match = re.search(r"found: \[([^\]]+)\]", issues)
    found = match.group(1) if match else ""
    return [
        "Each of the 10 topics must appear exactly 10 times. "
        f"Currently uneven: {found}. Please rebalance so every topic has exactly 10 riddles."
    ]


def _missing_columns_actions(issues: str) -> list[str]:
    if "missing required columns" not in issues:
        return []
    match = re.search(r"missing required columns: \[([^\]]+)\]", issues)
    cols = match.group(1) if match else "(see report)"
    return [
        f"Required columns are missing or named differently: {cols}. "
        "Please rename your columns to match the reference sheet exactly "
        "('Riddle (Original Language)' and 'Reference Answer (Original)'). "
        "Language-specific columns can stay, but the required ones must exist with these exact names."
    ]


def _tolerated_notes(row: dict[str, Any]) -> str:
    notes: list[str] = []
    tolerated = row.get("tolerated_issues", "") or ""

    if row.get("query_row_count_matches_expected") is False:
        notes.append(f"Row count is {row.get('query_row_count')} (expected 100).")

    if "Wildcard placeholder topic names remain" in tolerated:
        notes.append(
            "Wildcard placeholder names ('Wildcard 1 [rename]') still appear — please rename to your chosen topics."
        )

    if "Used sheet" in tolerated:
        match = re.search(r"Used sheet '([^']+)'", tolerated)
        if match:
            notes.append(
                f"Your worksheet is named '{match.group(1)}', not 'Riddles'. "
                "The validator handled it via fallback, but renaming to 'Riddles' is cleanest."
            )

    missing_answers = int(row.get("missing_answer_count") or 0)
    if missing_answers > 0:
        notes.append(f"{missing_answers} answer cell(s) empty.")

    duplicate_groups = int(row.get("duplicate_answer_group_count") or 0)
    if duplicate_groups > 0:
        notes.append(
            f"{duplicate_groups} duplicate answer group(s) — please check if intentional."
        )

    return " | ".join(notes)
