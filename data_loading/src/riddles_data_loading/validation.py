"""Validation logic for submitted riddle workbooks."""

from __future__ import annotations

import sys
from typing import TextIO

import numpy as np
import pandas as pd

from riddles_data_loading.config import ValidationConfig


def _is_missing(value: object) -> bool:
    if pd.isna(value):
        return True
    return isinstance(value, str) and value.strip() == ""


def _normalize_topic(value: object) -> object:
    if _is_missing(value):
        return np.nan
    if isinstance(value, str):
        return value.strip()
    return value


def _missing_mask(series: pd.Series) -> pd.Series:
    return series.apply(_is_missing)


def _row_labels(df: pd.DataFrame, mask: pd.Series) -> list[object]:
    if "Number" in df.columns:
        return df.loc[mask, "Number"].tolist()
    return df.index[mask].tolist()


def _row_labels_for_indexes(df: pd.DataFrame, indexes: list[object]) -> list[object]:
    if "Number" in df.columns:
        return df.loc[indexes, "Number"].tolist()
    return list(indexes)


def _normalize_answer(value: object) -> str | None:
    if _is_missing(value):
        return None
    return " ".join(str(value).strip().casefold().split())


def _answer_display_value(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


def _aligned_topic_rows(
    reference_sheet: pd.DataFrame,
    query_sheet: pd.DataFrame,
) -> tuple[list[dict[str, object]], bool]:
    can_align_by_number = (
        "Number" in reference_sheet.columns
        and "Number" in query_sheet.columns
        and reference_sheet["Number"].is_unique
        and query_sheet["Number"].is_unique
    )

    if can_align_by_number:
        ref_aligned = reference_sheet.copy()
        query_aligned = query_sheet.copy()

        ref_aligned["Topic"] = ref_aligned["Topic"].apply(_normalize_topic)
        query_aligned["Topic"] = query_aligned["Topic"].apply(_normalize_topic)

        ref_aligned = ref_aligned.set_index("Number")
        query_aligned = query_aligned.set_index("Number")
        common_numbers = sorted(set(ref_aligned.index) & set(query_aligned.index))

        return [
            {
                "row_label": number,
                "reference_topic": ref_aligned.loc[number, "Topic"],
                "query_topic": query_aligned.loc[number, "Topic"],
            }
            for number in common_numbers
        ], True

    common_length = min(len(reference_sheet), len(query_sheet))
    rows = []
    for idx in range(common_length):
        row_label = query_sheet.iloc[idx]["Number"] if "Number" in query_sheet.columns else idx
        rows.append(
            {
                "row_label": row_label,
                "reference_topic": _normalize_topic(reference_sheet.iloc[idx]["Topic"]),
                "query_topic": _normalize_topic(query_sheet.iloc[idx]["Topic"]),
            }
        )

    return rows, False


def validate_query_sheet_against_reference(
    reference_sheet: pd.DataFrame,
    query_sheet: pd.DataFrame,
    *,
    config: ValidationConfig | None = None,
) -> dict[str, object]:
    """Validate one submitted workbook against the reference sheet."""

    config = config or ValidationConfig()
    required_columns = list(config.required_columns)
    expected_topics = list(config.expected_topics)
    wildcard_topics = {config.wildcard_1, config.wildcard_2}

    blocking_issues: list[str] = []
    tolerated_issues: list[str] = []
    insights: dict[str, object] = {
        "expected_row_count": config.expected_rows,
        "reference_row_count": len(reference_sheet),
        "query_row_count": len(query_sheet),
        "reference_row_count_matches_expected": len(reference_sheet) == config.expected_rows,
        "query_row_count_matches_expected": len(query_sheet) == config.expected_rows,
    }

    if len(reference_sheet) != config.expected_rows:
        tolerated_issues.append(
            f"reference_sheet has {len(reference_sheet)} rows; expected {config.expected_rows}."
        )

    if len(query_sheet) != config.expected_rows:
        tolerated_issues.append(
            f"query_sheet has {len(query_sheet)} rows; expected {config.expected_rows}."
        )

    _validate_reference_sheet(reference_sheet, expected_topics, config, tolerated_issues, insights)
    _validate_required_query_columns(query_sheet, required_columns, blocking_issues, insights)
    _validate_answers(
        query_sheet,
        list(config.answer_columns),
        required_columns,
        blocking_issues,
        tolerated_issues,
        insights,
    )
    _summarize_query_missing_values(query_sheet, insights)
    _compare_columns(reference_sheet, query_sheet, required_columns, tolerated_issues, insights)
    _validate_number_column(
        query_sheet, config.expected_rows, blocking_issues, tolerated_issues, insights
    )
    _validate_topics(
        reference_sheet,
        query_sheet,
        config,
        wildcard_topics,
        blocking_issues,
        tolerated_issues,
        insights,
    )

    return {
        "passed": len(blocking_issues) == 0,
        "blocking_issues": blocking_issues,
        "tolerated_issues": tolerated_issues,
        "insights": insights,
    }


def _validate_reference_sheet(
    reference_sheet: pd.DataFrame,
    expected_topics: list[str],
    config: ValidationConfig,
    tolerated_issues: list[str],
    insights: dict[str, object],
) -> None:
    if "Number" not in reference_sheet.columns:
        tolerated_issues.append("reference_sheet is missing the 'Number' column.")
    else:
        expected_numbers = list(range(1, config.expected_rows + 1))
        actual_numbers = reference_sheet["Number"].tolist()

        if actual_numbers != expected_numbers:
            tolerated_issues.append(
                "reference_sheet['Number'] is not exactly 1 to 100 in order."
            )

    if "Topic" not in reference_sheet.columns:
        tolerated_issues.append("reference_sheet is missing the 'Topic' column.")
        return

    reference_topic_counts = (
        reference_sheet["Topic"].apply(_normalize_topic).value_counts(dropna=False).to_dict()
    )
    insights["reference_topic_counts"] = reference_topic_counts
    reference_count_issues = _find_topic_count_issues(
        reference_topic_counts,
        config.expected_topic_count,
    )
    insights["reference_topic_count_issues"] = reference_count_issues

    if config.require_ten_per_topic:
        for topic in expected_topics:
            count = reference_topic_counts.get(topic, 0)
            if count != config.expected_topic_count:
                tolerated_issues.append(
                    f"reference_sheet topic '{topic}' appears {count} times; "
                    f"expected {config.expected_topic_count}."
                )


def _validate_answers(
    query_sheet: pd.DataFrame,
    answer_columns: list[str],
    required_columns: list[str],
    blocking_issues: list[str],
    tolerated_issues: list[str],
    insights: dict[str, object],
) -> None:
    answer_checks = {}

    for col in answer_columns:
        if col not in query_sheet.columns:
            missing_mask = pd.Series(True, index=query_sheet.index)
            answer_checks[col] = {
                "column_missing": True,
                "missing_count": len(query_sheet),
                "missing_rows": _row_labels(query_sheet, missing_mask),
                "duplicate_group_count": 0,
                "duplicate_row_count": 0,
                "duplicate_groups": [],
            }
            continue

        missing_mask = _missing_mask(query_sheet[col])
        missing_rows = _row_labels(query_sheet, missing_mask)
        duplicate_groups = _find_duplicate_answer_groups(query_sheet, col)
        duplicate_row_count = sum(group["count"] for group in duplicate_groups)

        answer_checks[col] = {
            "column_missing": False,
            "missing_count": int(missing_mask.sum()),
            "missing_rows": missing_rows,
            "duplicate_group_count": len(duplicate_groups),
            "duplicate_row_count": duplicate_row_count,
            "duplicate_groups": duplicate_groups,
        }

        if missing_rows and col not in required_columns:
            blocking_issues.append(
                f"Answer column '{col}' has {len(missing_rows)} missing value(s)."
            )

        if duplicate_groups:
            tolerated_issues.append(
                f"Answer column '{col}' has {len(duplicate_groups)} duplicate answer "
                f"group(s) affecting {duplicate_row_count} rows."
            )

    insights["answer_checks"] = answer_checks


def _find_duplicate_answer_groups(
    query_sheet: pd.DataFrame,
    answer_column: str,
) -> list[dict[str, object]]:
    grouped_indexes: dict[str, list[object]] = {}
    display_values: dict[str, object] = {}

    for idx, value in query_sheet[answer_column].items():
        normalized_answer = _normalize_answer(value)
        if normalized_answer is None:
            continue
        grouped_indexes.setdefault(normalized_answer, []).append(idx)
        display_values.setdefault(normalized_answer, _answer_display_value(value))

    duplicate_groups = []
    for normalized_answer, indexes in sorted(grouped_indexes.items()):
        if len(indexes) <= 1:
            continue
        duplicate_groups.append(
            {
                "answer": display_values[normalized_answer],
                "normalized_answer": normalized_answer,
                "count": len(indexes),
                "rows": _row_labels_for_indexes(query_sheet, indexes),
            }
        )

    return duplicate_groups


def _find_topic_count_issues(
    topic_counts: dict[object, int],
    expected_topic_count: int,
) -> list[dict[str, object]]:
    issues = []

    for topic, count in topic_counts.items():
        if _is_missing(topic):
            continue
        if count != expected_topic_count:
            issues.append(
                {
                    "topic": topic,
                    "count": int(count),
                    "expected_count": expected_topic_count,
                }
            )

    return issues


def _validate_required_query_columns(
    query_sheet: pd.DataFrame,
    required_columns: list[str],
    blocking_issues: list[str],
    insights: dict[str, object],
) -> None:
    missing_required_columns = [col for col in required_columns if col not in query_sheet.columns]

    if missing_required_columns:
        blocking_issues.append(
            f"query_sheet is missing required columns: {missing_required_columns}"
        )

    required_missing_summary = {}
    for col in [col for col in required_columns if col in query_sheet.columns]:
        mask = _missing_mask(query_sheet[col])
        missing_count = int(mask.sum())

        if missing_count > 0:
            affected_rows = _row_labels(query_sheet, mask)
            required_missing_summary[col] = {
                "missing_count": missing_count,
                "affected_rows": affected_rows,
            }
            blocking_issues.append(
                f"Required column '{col}' has {missing_count} missing value(s)."
            )

    insights["required_missing_summary"] = required_missing_summary


def _summarize_query_missing_values(
    query_sheet: pd.DataFrame,
    insights: dict[str, object],
) -> None:
    insights["query_missing_values_by_column"] = {
        col: int(_missing_mask(query_sheet[col]).sum()) for col in query_sheet.columns
    }


def _compare_columns(
    reference_sheet: pd.DataFrame,
    query_sheet: pd.DataFrame,
    required_columns: list[str],
    tolerated_issues: list[str],
    insights: dict[str, object],
) -> None:
    reference_columns = list(reference_sheet.columns)
    missing_reference_columns = [col for col in reference_columns if col not in query_sheet.columns]
    extra_columns = [col for col in query_sheet.columns if col not in reference_columns]

    insights["missing_reference_columns_in_query"] = missing_reference_columns
    insights["extra_columns_in_query"] = extra_columns

    non_blocking_missing_columns = [
        col for col in missing_reference_columns if col not in required_columns
    ]
    if non_blocking_missing_columns:
        tolerated_issues.append(
            "query_sheet is missing non-blocking reference columns: "
            f"{non_blocking_missing_columns}"
        )

    if extra_columns:
        tolerated_issues.append(
            f"query_sheet has extra columns not in reference_sheet: {extra_columns}"
        )


def _validate_number_column(
    query_sheet: pd.DataFrame,
    expected_rows: int,
    blocking_issues: list[str],
    tolerated_issues: list[str],
    insights: dict[str, object],
) -> None:
    # The build forms a riddle id per row from {community}_{topic}_{Number}.
    # A missing 'Number' column (e.g. a sheet that used 'Id' instead) or a
    # duplicate number collapses rows into the same id, which the framework
    # dataset loader rejects. So these are blocking, not tolerated.
    if "Number" not in query_sheet.columns:
        blocking_issues.append(
            "query_sheet is missing the 'Number' column. Each riddle needs a "
            "'Number' (1..N) so it gets a unique id; if your sheet uses a "
            "different header (e.g. 'Id'), rename it to 'Number'."
        )
        insights["duplicate_numbers_in_query"] = []
        insights["missing_numbers_in_query"] = []
        return

    query_numbers = query_sheet["Number"]
    duplicate_numbers = query_numbers[query_numbers.duplicated() & query_numbers.notna()].tolist()
    insights["duplicate_numbers_in_query"] = duplicate_numbers

    if duplicate_numbers:
        blocking_issues.append(
            f"'Number' has duplicate value(s): {duplicate_numbers}. Each riddle "
            "needs a unique number; duplicates collide into the same riddle id."
        )

    numeric_numbers = pd.to_numeric(query_numbers, errors="coerce")
    valid_numbers = set(numeric_numbers.dropna().astype(int).tolist())
    expected_number_set = set(range(1, expected_rows + 1))
    missing_numbers = sorted(expected_number_set - valid_numbers)

    insights["missing_numbers_in_query"] = missing_numbers

    if missing_numbers:
        tolerated_issues.append(
            f"query_sheet is missing these expected 'Number' values: {missing_numbers}"
        )


def _validate_topics(
    reference_sheet: pd.DataFrame,
    query_sheet: pd.DataFrame,
    config: ValidationConfig,
    wildcard_topics: set[str],
    blocking_issues: list[str],
    tolerated_issues: list[str],
    insights: dict[str, object],
) -> None:
    if "Topic" not in reference_sheet.columns or "Topic" not in query_sheet.columns:
        insights["query_topic_counts"] = {}
        insights["wildcard_rename_summary"] = {}
        insights["wildcard_replacement_topics"] = []
        insights["wildcard_1_new_topic"] = None
        insights["wildcard_2_new_topic"] = None
        insights["topic_mismatches"] = []
        return

    query_topics = query_sheet["Topic"].apply(_normalize_topic)
    query_topic_counts = query_topics.value_counts(dropna=False).to_dict()
    topic_count_issues = _find_topic_count_issues(
        query_topic_counts,
        config.expected_topic_count,
    )
    insights["query_topic_counts"] = query_topic_counts
    insights["query_topic_count_issues"] = topic_count_issues

    if config.require_ten_per_topic and topic_count_issues:
        issue_details = [
            f"{issue['topic']}={issue['count']}" for issue in topic_count_issues
        ]
        blocking_issues.append(
            "query_sheet topic counts must be exactly "
            f"{config.expected_topic_count}; found: {issue_details}"
        )

    if config.require_ten_per_topic:
        non_missing_topics = [t for t in query_topic_counts.keys() if not _is_missing(t)]
        expected_distinct = len(config.expected_topics)
        if len(non_missing_topics) != expected_distinct:
            blocking_issues.append(
                f"query_sheet must have exactly {expected_distinct} distinct topics; "
                f"found {len(non_missing_topics)}: "
                f"{sorted(non_missing_topics, key=str)}"
            )

    wildcard_summary = _validate_wildcard_replacements_by_topic_set(
        query_sheet,
        query_topic_counts,
        config,
        wildcard_topics,
        blocking_issues,
        tolerated_issues,
    )
    replacement_topics = wildcard_summary["replacement_topics"]

    insights["wildcard_rename_summary"] = wildcard_summary
    insights["wildcard_replacement_topics"] = replacement_topics
    insights["wildcard_1_new_topic"] = (
        replacement_topics[0] if len(replacement_topics) == 2 else None
    )
    insights["wildcard_2_new_topic"] = (
        replacement_topics[1] if len(replacement_topics) == 2 else None
    )

    aligned_rows, aligned_by_number = _aligned_topic_rows(reference_sheet, query_sheet)
    if not aligned_by_number:
        tolerated_issues.append(
            "Rows were compared by position because a unique 'Number' column was not "
            "available in both sheets."
        )

    topic_mismatches = _find_non_wildcard_topic_mismatches(aligned_rows, wildcard_topics)
    insights["topic_mismatches"] = topic_mismatches

    if topic_mismatches:
        tolerated_issues.append(
            f"query_sheet has {len(topic_mismatches)} non-wildcard topic mismatch(es)."
        )


def _validate_wildcard_replacements_by_topic_set(
    query_sheet: pd.DataFrame,
    query_topic_counts: dict[object, int],
    config: ValidationConfig,
    wildcard_topics: set[str],
    blocking_issues: list[str],
    tolerated_issues: list[str],
) -> dict[str, object]:
    standard_topics = {
        topic for topic in config.expected_topics if topic not in wildcard_topics
    }
    query_topics = _sorted_non_missing_values(query_topic_counts.keys())
    replacement_topics = [
        topic
        for topic in query_topics
        if topic not in standard_topics and topic not in wildcard_topics
    ]
    missing_standard_topics = [
        topic for topic in sorted(standard_topics) if topic not in query_topic_counts
    ]

    unresolved_placeholders = {}
    query_topics_normalized = query_sheet["Topic"].apply(_normalize_topic)

    for wildcard in [config.wildcard_1, config.wildcard_2]:
        mask = query_topics_normalized == wildcard
        unresolved_placeholders[wildcard] = _row_labels(query_sheet, mask)

    unresolved_rows = [
        row
        for rows in unresolved_placeholders.values()
        for row in rows
    ]

    # Per the README, wildcard placeholders must be renamed and there must be
    # exactly two distinct replacement topics. When the strict topic check is
    # enabled, these are blocking; otherwise they are recorded as tolerated.
    target_list = blocking_issues if config.require_ten_per_topic else tolerated_issues

    if unresolved_rows:
        target_list.append(
            "Wildcard placeholder topic names remain in query_sheet on rows: "
            f"{unresolved_rows}"
        )

    if len(replacement_topics) != 2:
        target_list.append(
            "Wildcard replacements are inferred from the full set of submitted topics; "
            f"expected 2 non-standard topics, found {len(replacement_topics)}: "
            f"{replacement_topics}"
        )

    if missing_standard_topics:
        target_list.append(
            f"query_sheet is missing expected standard topics: {missing_standard_topics}"
        )

    return {
        "method": "full_topic_set",
        "expected_replacement_topic_count": 2,
        "replacement_topics": replacement_topics,
        "replacement_topic_count": len(replacement_topics),
        "standard_topics": sorted(standard_topics),
        "missing_standard_topics": missing_standard_topics,
        "unresolved_placeholder_rows": unresolved_placeholders,
    }


def _sorted_non_missing_values(values) -> list[object]:
    return sorted(
        [value for value in values if not _is_missing(value)],
        key=lambda value: str(value),
    )


def _find_non_wildcard_topic_mismatches(
    aligned_rows: list[dict[str, object]],
    wildcard_topics: set[str],
) -> list[dict[str, object]]:
    topic_mismatches = []

    for row in aligned_rows:
        ref_topic = row["reference_topic"]
        query_topic = row["query_topic"]

        if ref_topic in wildcard_topics:
            continue
        if not _is_missing(query_topic) and query_topic != ref_topic:
            topic_mismatches.append(
                {
                    "row": row["row_label"],
                    "reference_topic": ref_topic,
                    "query_topic": query_topic,
                }
            )

    return topic_mismatches


def print_validation_report(
    result: dict[str, object],
    *,
    stream: TextIO = sys.stdout,
) -> None:
    """Pretty-print a validation result."""

    print("PASSED:", result["passed"], file=stream)
    _print_issue_list("BLOCKING ISSUES", result["blocking_issues"], stream=stream)
    _print_issue_list("TOLERATED ISSUES", result["tolerated_issues"], stream=stream)

    print("\nKEY INSIGHTS:", file=stream)
    for key in [
        "reference_row_count",
        "expected_row_count",
        "query_row_count",
        "query_row_count_matches_expected",
        "wildcard_1_new_topic",
        "wildcard_2_new_topic",
        "answer_checks",
        "required_missing_summary",
        "query_missing_values_by_column",
        "missing_reference_columns_in_query",
        "extra_columns_in_query",
        "duplicate_numbers_in_query",
        "missing_numbers_in_query",
        "topic_mismatches",
        "wildcard_rename_summary",
    ]:
        if key in result["insights"]:
            print(f"\n{key}:", file=stream)
            print(result["insights"][key], file=stream)


def _print_issue_list(title: str, issues: object, *, stream: TextIO) -> None:
    print(f"\n{title}:", file=stream)
    if issues:
        for issue in issues:
            print("-", issue, file=stream)
    else:
        print("- None", file=stream)
