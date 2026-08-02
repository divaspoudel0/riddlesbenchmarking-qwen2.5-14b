# Riddles Benchmark Data Loading

This package downloads submitted riddle workbooks and validates each workbook
against the benchmark reference sheet.

## Setup

```bash
python -m pip install -r requirements.txt
```

## Run the full validation

```bash
python validate_submissions.py --download
```

The command downloads the reference Google Sheet and the submitted workbooks,
then writes:

- `reports/validation_summary.csv`
- `reports/validation_results.json`
- `reports/contributor_feedback.csv` (human-readable feedback per submission)
- `reports/jsonl/*.jsonl`
- `reports/passed_jsonl/*.jsonl`

The summary CSV includes `failure_reason` and `blocking_issues` columns so each
failed submission can be inspected without opening the full JSON report.

Use `--no-download` to validate files that are already present locally:

```bash
python validate_submissions.py --no-download --data-dir data/submitted_riddles
```

Or point directly at a local folder that already contains `reference_sheet.xlsx`
and submitted `.xlsx` workbooks:

```bash
python validate_submissions.py --local-folder path/to/submitted_riddles
```

Use `--redownload` to fetch fresh copies even when local downloads already
exist:

```bash
python validate_submissions.py --redownload
```

If a submitted workbook does not contain a worksheet named `Riddles`, the CLI
falls back to the workbook's first worksheet and records that fallback as a
tolerated issue in the report.

The validator intentionally scans `.xlsx` submissions, matching the original
notebook workflow. Other downloaded exports, such as `.csv` files, are left in
the data directory but are not included in the validation report.

By default, every submitted topic must appear exactly 10 times. Use
`--allow-topic-count-mismatch` to report topic-count issues without failing the
submission:

```bash
python validate_submissions.py --no-download --allow-topic-count-mismatch
```

## Project Layout

- `src/riddles_data_loading/config.py`: default URLs, filenames, and validation constants.
- `src/riddles_data_loading/downloader.py`: Google Sheet and Drive download helpers.
- `src/riddles_data_loading/io.py`: workbook discovery and sheet loading.
- `src/riddles_data_loading/validation.py`: validation rules.
- `src/riddles_data_loading/reports.py`: CSV and JSON report writing.
- `src/riddles_data_loading/cli.py`: argument parsing and pipeline orchestration.
- `validate_submissions.py`: root script for `python validate_submissions.py ...`.

## What Is Checked

Blocking checks determine whether a workbook passes:

- Required columns are present.
- Required values are filled.
- `Wildcard 1 [rename]` is renamed to exactly one replacement topic.
- `Wildcard 2 [rename]` is renamed to exactly one different replacement topic.

Non-blocking checks are included in the report as tolerated issues, including
row-count mismatches, answer duplicates, non-blocking column differences, and
wildcard replacement naming issues. Wildcard replacement topics are inferred
from the full set of submitted topic names, so reordered rows do not fail
validation.
