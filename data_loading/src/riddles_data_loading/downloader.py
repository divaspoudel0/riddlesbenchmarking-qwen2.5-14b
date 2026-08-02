"""Download helpers for public Google Sheet and Google Drive sources."""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlretrieve

from riddles_data_loading.config import (
    DEFAULT_DRIVE_FOLDER_URL,
    DEFAULT_REFERENCE_FILENAME,
    DEFAULT_REFERENCE_GID,
    DEFAULT_REFERENCE_SHEET_ID,
)


def build_sheet_export_url(sheet_id: str, gid: str) -> str:
    """Return the XLSX export URL for a Google Sheet tab."""

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx&gid={gid}"


def download_reference_sheet(
    output_dir: Path,
    *,
    sheet_id: str = DEFAULT_REFERENCE_SHEET_ID,
    gid: str = DEFAULT_REFERENCE_GID,
    filename: str = DEFAULT_REFERENCE_FILENAME,
    force: bool = False,
) -> Path:
    """Download the reference Google Sheet as an XLSX file."""

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    if output_path.exists() and not force:
        return output_path

    url = build_sheet_export_url(sheet_id, gid)
    urlretrieve(url, output_path)
    return output_path


def download_submission_folder(
    output_dir: Path,
    *,
    folder_url: str = DEFAULT_DRIVE_FOLDER_URL,
    force: bool = False,
    quiet: bool = False,
) -> list[Path]:
    """Download submitted workbooks from a public Google Drive folder."""

    try:
        import gdown
    except ImportError as exc:
        raise RuntimeError(
            "gdown is required to download the Google Drive folder. "
            "Install dependencies with `python -m pip install -e .`."
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)

    if force:
        _remove_existing_drive_folder_files(
            gdown=gdown,
            folder_url=folder_url,
            output_dir=output_dir,
            quiet=quiet,
        )

    downloaded_files = gdown.download_folder(
        url=folder_url,
        output=str(output_dir),
        quiet=quiet,
        use_cookies=False,
        resume=not force,
    )

    return [Path(path) for path in downloaded_files or []]


def _remove_existing_drive_folder_files(
    *,
    gdown,
    folder_url: str,
    output_dir: Path,
    quiet: bool,
) -> None:
    """Remove local files that correspond to the remote Drive folder listing."""

    files_to_download = gdown.download_folder(
        url=folder_url,
        output=str(output_dir),
        quiet=quiet,
        use_cookies=False,
        skip_download=True,
    )

    for drive_file in files_to_download or []:
        local_path = Path(drive_file.local_path)
        if local_path.exists() and local_path.is_file():
            local_path.unlink()
