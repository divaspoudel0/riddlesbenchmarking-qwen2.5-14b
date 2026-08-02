"""Default configuration for the riddle workbook validation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_REFERENCE_SHEET_ID = "1AdULGg75JVx6NVCnY0Oh9lr3p6ZSAbhMY1Z5rjkRqW8"
DEFAULT_REFERENCE_GID = "0"
DEFAULT_DRIVE_FOLDER_URL = (
    "https://drive.google.com/drive/folders/1zlcqFiJy7KAZsT6QRX2quy5N32XW09iW"
)
DEFAULT_DRIVE_FOLDER_URL_V1 = (
    "https://drive.google.com/drive/folders/1mbjDUImGF3c9KOL3YXHIePBp6zy9IMDe"
)

DEFAULT_DATA_DIR = Path("data/submitted_riddles")
DEFAULT_DATA_DIR_V1 = Path("data/submitted_riddles_v1")
DEFAULT_REPORT_DIR = Path("reports")
DEFAULT_REPORT_DIR_V1 = Path("reports_v1")

# Submission batches. Each batch has its own Drive folder, local submission
# directory, and report directory so validating one batch never overwrites
# another batch's reports. v0 keeps the original paths so existing behavior is
# unchanged.
DEFAULT_RUN_BATCH = "v0"
RUN_BATCHES: dict[str, dict[str, object]] = {
    "v0": {
        "folder_url": DEFAULT_DRIVE_FOLDER_URL,
        "data_dir": DEFAULT_DATA_DIR,
        "report_dir": DEFAULT_REPORT_DIR,
    },
    "v1": {
        "folder_url": DEFAULT_DRIVE_FOLDER_URL_V1,
        "data_dir": DEFAULT_DATA_DIR_V1,
        "report_dir": DEFAULT_REPORT_DIR_V1,
    },
}
DEFAULT_REFERENCE_FILENAME = "reference_sheet.xlsx"
DEFAULT_SHEET_NAME = "Riddles"
DEFAULT_EXPECTED_ROWS = 100
DEFAULT_EXPECTED_TOPIC_COUNT = 10

REQUIRED_COLUMNS = [
    "Topic",
    "Author",
    "Riddle (Original Language)",
    "Reference Answer (Original)",
]

ANSWER_COLUMNS = [
    "Reference Answer (Original)",
]

EXPECTED_TOPICS = [
    "Politics",
    "History",
    "Geography",
    "Arts",
    "Sports",
    "National Heritage",
    "Kid's World",
    "Everyday Life",
    "Wildcard 1 [rename]",
    "Wildcard 2 [rename]",
]

WILDCARD_1 = "Wildcard 1 [rename]"
WILDCARD_2 = "Wildcard 2 [rename]"


@dataclass(frozen=True)
class ValidationConfig:
    """Validation settings shared by the CLI and library callers."""

    expected_rows: int = DEFAULT_EXPECTED_ROWS
    expected_topic_count: int = DEFAULT_EXPECTED_TOPIC_COUNT
    require_ten_per_topic: bool = True
    required_columns: tuple[str, ...] = tuple(REQUIRED_COLUMNS)
    answer_columns: tuple[str, ...] = tuple(ANSWER_COLUMNS)
    expected_topics: tuple[str, ...] = tuple(EXPECTED_TOPICS)
    wildcard_1: str = WILDCARD_1
    wildcard_2: str = WILDCARD_2
