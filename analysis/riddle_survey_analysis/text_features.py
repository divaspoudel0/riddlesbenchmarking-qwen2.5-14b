from __future__ import annotations
from pathlib import Path
import re


def find_repo_root(start: Path)-> Path:
    for folder in [start, *start.parents]:
        if (folder/"analysis"/"style.py").exists():
            return folder
    raise FileNotFoundError(f"Couldn't find analysis/style.py above {start}")

REPO_ROOT= find_repo_root(Path(__file__).resolve().parent)
CSV_DIR= Path(__file__).resolve().parent/ "csv"
FIGURES_DIR= Path(__file__).resolve().parent/"figures"
