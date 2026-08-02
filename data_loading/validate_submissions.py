"""Run the riddle submission validation pipeline.

This root-level wrapper keeps the public entry point simple:

    python validate_submissions.py --download
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from riddles_data_loading.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
