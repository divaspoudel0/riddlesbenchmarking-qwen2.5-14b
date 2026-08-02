"""File discovery and workbook loading utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from riddles_data_loading.config import DEFAULT_REFERENCE_FILENAME, DEFAULT_SHEET_NAME


@dataclass(frozen=True)
class SheetLoadResult:
    """A loaded sheet plus metadata about how it was selected."""

    dataframe: pd.DataFrame
    sheet_name: str
    used_fallback: bool = False
    phantom_rows_stripped: int = 0


def _strip_phantom_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Drop trailing rows where the primary riddle column is null.

    Excel preserves "touched" cell ranges even after content is deleted,
    causing pd.read_excel to return empty trailing rows. These were being
    counted as incomplete riddles and producing false "missing value"
    validation errors. Strip rows where the riddle column is null so
    downstream checks see the real row count.
    """
    riddle_col = "Riddle (Original Language)"
    if riddle_col not in df.columns:
        return df, 0
    before = len(df)
    cleaned = df.loc[df[riddle_col].notna()].reset_index(drop=True)
    return cleaned, before - len(cleaned)


def read_riddle_sheet(path: Path, *, sheet_name: str = DEFAULT_SHEET_NAME) -> pd.DataFrame:
    """Read a workbook's riddle sheet into a DataFrame."""

    return load_riddle_sheet(path, sheet_name=sheet_name).dataframe


def load_riddle_sheet(
    path: Path,
    *,
    sheet_name: str = DEFAULT_SHEET_NAME,
    fallback_to_first_sheet: bool = False,
) -> SheetLoadResult:
    """Read a workbook sheet and optionally fall back to its first worksheet."""

    try:
        raw = pd.read_excel(path, sheet_name=sheet_name)
        cleaned, stripped = _strip_phantom_rows(raw)
        return SheetLoadResult(
            dataframe=cleaned,
            sheet_name=sheet_name,
            phantom_rows_stripped=stripped,
        )
    except ValueError as exc:
        if not fallback_to_first_sheet or "Worksheet named" not in str(exc):
            raise

    workbook = pd.ExcelFile(path)
    first_sheet = workbook.sheet_names[0]
    raw = pd.read_excel(workbook, sheet_name=first_sheet)
    cleaned, stripped = _strip_phantom_rows(raw)
    return SheetLoadResult(
        dataframe=cleaned,
        sheet_name=first_sheet,
        used_fallback=True,
        phantom_rows_stripped=stripped,
    )


def discover_submission_workbooks(
    data_dir: Path,
    *,
    reference_filename: str = DEFAULT_REFERENCE_FILENAME,
) -> list[Path]:
    """Find submitted XLSX files, excluding the downloaded reference sheet."""

    files = []
    for path in data_dir.rglob("*.xlsx"):
        if path.name.startswith("~$"):
            continue
        if path.name == reference_filename:
            continue
        files.append(path)

    return sorted(files)
