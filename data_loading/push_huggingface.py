"""Push the HuggingFace export to a private dataset repo.

Reads hf_export/ (parquet + card) and uploads it to a HuggingFace dataset repo,
creating it as PRIVATE if it does not exist. Safe to re-run: re-uploading
updates the files, which is how review iterations work.

The write token is read from the HF_TOKEN environment variable and is never
stored in this file or the repo. Set it for one shell session before running:

    export HF_TOKEN=hf_...
    uv run python push_huggingface.py
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

HERE = Path(__file__).parent
DEFAULT_EXPORT_DIR = HERE / "hf_export"
REPO_ID = "CohereLabsCommunity/multicultural-riddles-benchmark"


def main(export_dir: Path, repo_id: str, private: bool) -> None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit(
            "HF_TOKEN not set. Export your write token first:\n"
            "  export HF_TOKEN=hf_...\n"
            "It is read from the environment and never stored."
        )

    readme = export_dir / "README.md"
    parquet = export_dir / "data" / "test-00000-of-00001.parquet"
    for p in (readme, parquet):
        if not p.exists():
            sys.exit(f"Missing {p}. Run export_huggingface.py first.")

    api = HfApi(token=token)

    if not private:
        # Guard against an accidental public push.
        confirm = input(
            f"About to create/keep {repo_id} PUBLIC. The data is scrapeable once "
            "public. Type 'yes' to proceed: "
        )
        if confirm.strip().lower() != "yes":
            sys.exit("Aborted. Re-run without --public to push privately.")

    api.create_repo(
        repo_id=repo_id,
        repo_type="dataset",
        private=private,
        exist_ok=True,
    )
    print(f"Repo ready: {repo_id}")

    api.upload_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=str(export_dir),
        commit_message="Add Multicultural Riddles Benchmark pilot (parquet + card)",
        ignore_patterns=["*.DS_Store", "**/.DS_Store"],
    )

    info = api.dataset_info(repo_id)
    print(f"Uploaded to https://huggingface.co/datasets/{repo_id}")
    print(f"  private: {info.private}")
    if info.private:
        print("Repo is private. Share with reviewers; make public only after sign-off.")
    else:
        print("WARNING: repo is PUBLIC.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Push the HF export to a private dataset repo."
    )
    p.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    p.add_argument("--repo-id", default=REPO_ID)
    p.add_argument(
        "--public",
        action="store_true",
        help="Create/keep the repo public (asks for confirmation). Default: private.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.export_dir, args.repo_id, private=not args.public)
