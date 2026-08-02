"""Command-line interface for the riddle workbook validation pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from riddles_data_loading.config import (
    DEFAULT_REFERENCE_FILENAME,
    DEFAULT_REFERENCE_GID,
    DEFAULT_REFERENCE_SHEET_ID,
    DEFAULT_RUN_BATCH,
    DEFAULT_SHEET_NAME,
    RUN_BATCHES,
    ValidationConfig,
)
from riddles_data_loading.downloader import (
    download_reference_sheet,
    download_submission_folder,
)
from riddles_data_loading.io import (
    discover_submission_workbooks,
    load_riddle_sheet,
    read_riddle_sheet,
)
from riddles_data_loading.reports import (
    summarize_result,
    write_reports,
    write_submission_jsonl,
)
from riddles_data_loading.contributor_feedback import write_contributor_feedback
from riddles_data_loading.validation import validate_query_sheet_against_reference


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download and validate submitted riddle benchmark workbooks."
    )
    download_group = parser.add_mutually_exclusive_group()
    download_group.add_argument(
        "--download",
        action="store_true",
        help="Download the reference sheet and Google Drive folder before validating.",
    )
    download_group.add_argument(
        "--no-download",
        action="store_true",
        help="Validate local files only.",
    )
    download_group.add_argument(
        "--redownload",
        "--force-download",
        dest="redownload",
        action="store_true",
        help="Download sources again even if local copies already exist.",
    )
    download_group.add_argument(
        "--local-folder",
        type=Path,
        help="Load reference and submission workbooks from a local folder.",
    )
    parser.add_argument(
        "--run-batch",
        choices=sorted(RUN_BATCHES),
        default=DEFAULT_RUN_BATCH,
        help=(
            "Submission batch to download and validate. Selects the Drive folder, "
            "data directory, and report directory for that batch unless those are "
            "passed explicitly. Defaults to v0."
        ),
    )
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument(
        "--jsonl-dir",
        type=Path,
        help="Directory for per-submission JSONL exports. Defaults to REPORT_DIR/jsonl.",
    )
    parser.add_argument(
        "--passed-jsonl-dir",
        type=Path,
        help=(
            "Directory for JSONL exports of passing submissions only. "
            "Defaults to REPORT_DIR/passed_jsonl."
        ),
    )
    parser.add_argument("--reference-file", type=Path)
    parser.add_argument("--reference-filename", default=DEFAULT_REFERENCE_FILENAME)
    parser.add_argument("--sheet-name", default=DEFAULT_SHEET_NAME)
    parser.add_argument("--expected-rows", type=int, default=100)
    topic_group = parser.add_mutually_exclusive_group()
    topic_group.add_argument(
        "--require-ten-per-topic",
        action="store_true",
        help="Fail submissions whose topic counts are not exactly 10 per topic. This is the default.",
    )
    topic_group.add_argument(
        "--allow-topic-count-mismatch",
        action="store_true",
        help="Report topic-count issues without failing the submission.",
    )
    parser.add_argument("--sheet-id", default=DEFAULT_REFERENCE_SHEET_ID)
    parser.add_argument("--gid", default=DEFAULT_REFERENCE_GID)
    parser.add_argument("--folder-url", default=None)
    parser.add_argument("--quiet", action="store_true", help="Reduce download output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)


def run(args: argparse.Namespace) -> int:
    batch = RUN_BATCHES[args.run_batch]
    data_dir = args.local_folder or args.data_dir or batch["data_dir"]
    report_dir = args.report_dir or batch["report_dir"]
    folder_url = args.folder_url or batch["folder_url"]
    reference_path = args.reference_file or data_dir / args.reference_filename
    should_download = (
        not args.local_folder
        and (args.download
        or args.redownload
        or (not args.no_download and not reference_path.exists()))
    )

    if should_download:
        print("Downloading reference sheet...")
        reference_path = download_reference_sheet(
            data_dir,
            sheet_id=args.sheet_id,
            gid=args.gid,
            filename=args.reference_filename,
            force=args.redownload,
        )
        print("Downloading submitted workbooks...")
        download_submission_folder(
            data_dir,
            folder_url=folder_url,
            force=args.redownload,
            quiet=args.quiet,
        )

    if not reference_path.exists():
        raise FileNotFoundError(
            f"Reference workbook not found at {reference_path}. "
            "Run with --download or pass --reference-file."
        )

    reference_sheet = read_riddle_sheet(reference_path, sheet_name=args.sheet_name)
    workbook_paths = discover_submission_workbooks(
        data_dir,
        reference_filename=args.reference_filename,
    )

    if not workbook_paths:
        raise FileNotFoundError(f"No submitted .xlsx workbooks found under {data_dir}.")

    config = ValidationConfig(
        expected_rows=args.expected_rows,
        require_ten_per_topic=not args.allow_topic_count_mismatch,
    )
    jsonl_dir = args.jsonl_dir or report_dir / "jsonl"
    passed_jsonl_dir = args.passed_jsonl_dir or report_dir / "passed_jsonl"
    _clear_jsonl_outputs(jsonl_dir)
    _clear_jsonl_outputs(passed_jsonl_dir)
    full_results: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for workbook_path in workbook_paths:
        result, dataframe, loaded_sheet_name = _validate_workbook(
            workbook_path,
            reference_sheet,
            args.sheet_name,
            config,
        )
        if dataframe is not None and loaded_sheet_name is not None:
            jsonl_path = write_submission_jsonl(
                dataframe,
                workbook_path,
                loaded_sheet_name,
                jsonl_dir,
            )
            result["insights"]["jsonl_path"] = str(jsonl_path)
            if result["passed"]:
                passed_jsonl_path = write_submission_jsonl(
                    dataframe,
                    workbook_path,
                    loaded_sheet_name,
                    passed_jsonl_dir,
                )
                result["insights"]["passed_jsonl_path"] = str(passed_jsonl_path)
            else:
                result["insights"]["passed_jsonl_path"] = None
        full_results.append({"file": str(workbook_path), "result": result})
        summary_rows.append(summarize_result(workbook_path, result))

    csv_path, json_path = write_reports(full_results, summary_rows, report_dir)
    feedback_path = write_contributor_feedback(summary_rows, report_dir)
    _print_run_summary(summary_rows, csv_path, json_path, feedback_path, jsonl_dir, passed_jsonl_dir)

    return 0 if all(row["passed"] for row in summary_rows) else 1


def _validate_workbook(
    workbook_path: Path,
    reference_sheet,
    sheet_name: str,
    config: ValidationConfig,
) -> tuple[dict[str, Any], Any | None, str | None]:
    try:
        loaded_sheet = load_riddle_sheet(
            workbook_path,
            sheet_name=sheet_name,
            fallback_to_first_sheet=True,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            {
                "passed": False,
                "blocking_issues": [f"Failed to read workbook sheet '{sheet_name}': {exc}"],
                "tolerated_issues": [],
                "insights": {
                    "query_row_count": None,
                    "loaded_sheet_name": None,
                    "used_sheet_fallback": False,
                    "jsonl_path": None,
                    "passed_jsonl_path": None,
                },
            },
            None,
            None,
        )

    result = validate_query_sheet_against_reference(
        reference_sheet=reference_sheet,
        query_sheet=loaded_sheet.dataframe,
        config=config,
    )
    result["insights"]["loaded_sheet_name"] = loaded_sheet.sheet_name
    result["insights"]["used_sheet_fallback"] = loaded_sheet.used_fallback

    if loaded_sheet.used_fallback:
        result["tolerated_issues"].insert(
            0,
            f"Used sheet '{loaded_sheet.sheet_name}' because requested sheet "
            f"'{sheet_name}' was not found.",
        )

    return result, loaded_sheet.dataframe, loaded_sheet.sheet_name


def _print_run_summary(
    summary_rows: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    feedback_path: Path,
    jsonl_dir: Path,
    passed_jsonl_dir: Path,
) -> None:
    total = len(summary_rows)
    passed = sum(1 for row in summary_rows if row["passed"])
    failed = total - passed

    print(f"Validated {total} workbook(s): {passed} passed, {failed} failed.")
    print(f"Summary CSV: {csv_path}")
    print(f"Full JSON: {json_path}")
    print(f"Contributor feedback CSV: {feedback_path}")
    print(f"Submission JSONL directory: {jsonl_dir}")
    print(f"Passed submission JSONL directory: {passed_jsonl_dir}")

    row_count_mismatches = [
        row for row in summary_rows if row["query_row_count_matches_expected"] is False
    ]
    if row_count_mismatches:
        print("\nWorkbooks with non-standard row counts:")
        for row in row_count_mismatches:
            print(
                f"- {row['file']} ({row['query_row_count']} rows; "
                f"expected {row['expected_row_count']})"
            )

    if failed:
        print("\nFailed workbooks:")
        for row in summary_rows:
            if not row["passed"]:
                print(f"- {row['file']} ({row['blocking_issue_count']} blocking issue(s))")


def _clear_jsonl_outputs(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.glob("*.jsonl"):
        if path.is_file():
            path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
