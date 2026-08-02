"""Load v0 model run results into one tidy DataFrame.

Walks a directory of run folders (downloaded from the shared Drive folder
RiddleBenchmarking/Responses_v0), extracts the model answer from each row's
raw_response, and produces one row per (riddle_id, model, condition).

Folder quirks are handled here, in code, so the Drive data never needs
hand-fixing:
- some runners prefixed filenames (13_tiny-aya-fire_results.jsonl); files
  are found by glob, not exact name
- manifest.json / run_metadata.json are optional; everything needed lives
  in results.jsonl rows and run_config.json
- two claude-opus-4-7 runs share a model_name and differ only by
  reasoning_mode, so model identity is (model_name, reasoning_mode)

Usage:
    python load_results.py [runs_dir] [out_path]
    defaults: data/responses_v0  ->  data/processed/results_tidy.parquet
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

# Folders excluded from analysis, with reasons. Keep data on disk untouched;
# exclusions are documented here so a fresh Drive download reproduces the
# same analysis set.
EXCLUDED_FOLDERS: dict[str, str] = {
    "28_param-1-2.9B": "removed from benchmarking (config says smoke_test)",
}

# Individual riddles excluded from analysis, with reasons. The riddle stays
# in every run folder (models did answer it); we skip it in scoring because
# the shipped v0 text was later found to be wrong, so those answers are
# answers to the wrong riddle. The corrected riddle is re-evaluated fresh in
# a later dataset version, not backfilled into v0. See RIDDLE_CORRECTIONS.md.
EXCLUDED_RIDDLES: dict[str, str] = {
    "spanish_cuba_history_016": (
        "wrong riddle text shipped in v0; contributor corrected the source "
        "row, re-evaluated in v2 (flagged 23 Jul 2026)"
    ),
}

# Columns copied through from each results.jsonl row.
ROW_COLUMNS = [
    "instance_id",
    "run_id",
    "riddle_id",
    "condition_id",
    "riddle_language_presented",
    "is_hint_provided",
    "instance_community",
    "instance_topic",
    "instance_language",
    "reference_answer_original",
    "reference_answer_english",
    "model_name",
    "model_id",
    "reasoning_mode",
    "generation_status",
    "input_tokens",
    "output_tokens",
    "raw_response",
]

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_ANSWER_RE = re.compile(r'"riddle_answer"\s*:\s*"((?:[^"\\]|\\.)*)"')
# Amazon Nova Micro emits pseudo-JSON with single-quoted values:
#   { "riddle_answer": 'القاهرة', "reasoning": '...' }
_ANSWER_SQ_RE = re.compile(r'"riddle_answer"\s*:\s*\'(.*?)\'\s*,')


def extract_answer(raw_response: object) -> tuple[str | None, str]:
    """Extract the riddle_answer from a raw model response.

    Returns (answer, parse_status) where parse_status is one of
    'json', 'regex', 'empty', 'unparsed'.
    """
    if raw_response is None:
        return None, "empty"
    text = str(raw_response).strip()
    if not text:
        return None, "empty"
    cleaned = _FENCE_RE.sub("", text).strip()
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict) and "riddle_answer" in obj:
            ans = obj["riddle_answer"]
            ans = None if ans is None else str(ans).strip()
            return (ans or None), "json"
    except (json.JSONDecodeError, ValueError):
        pass
    m = _ANSWER_RE.search(cleaned)
    if m:
        try:
            ans = json.loads(f'"{m.group(1)}"').strip()
        except (json.JSONDecodeError, ValueError):
            ans = m.group(1).strip()
        return (ans or None), "regex"
    m = _ANSWER_SQ_RE.search(cleaned)
    if m:
        ans = m.group(1).strip()
        return (ans or None), "regex_single_quote"
    return None, "unparsed"


def find_file(folder: Path, pattern: str) -> Path | None:
    matches = sorted(folder.glob(pattern))
    return matches[0] if matches else None


def load_run_folder(folder: Path) -> pd.DataFrame | None:
    """Load one run folder into a DataFrame, or None if unusable."""
    results_path = find_file(folder, "*results*.jsonl")
    if results_path is None:
        print(f"  SKIP {folder.name}: no results jsonl found")
        return None

    # Search-enabled runs (e.g. GPT5.5 with web search) are a separate
    # evaluation category: open-web retrieval is not comparable to
    # closed-book recall. The flag lives in run_config.json.
    search_enabled = False
    config_path = find_file(folder, "*run_config*.json")
    if config_path is not None:
        try:
            with open(config_path, encoding="utf-8") as f:
                search_enabled = bool(json.load(f).get("search_enabled", False))
        except (json.JSONDecodeError, OSError):
            pass

    rows = []
    with open(results_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            row = {c: r.get(c) for c in ROW_COLUMNS}
            answer, parse_status = extract_answer(r.get("raw_response"))
            row["answer_text"] = answer
            row["answer_parse_status"] = parse_status
            rows.append(row)

    df = pd.DataFrame(rows)
    df["source_folder"] = folder.name
    df["eval_category"] = "search_enabled" if search_enabled else "closed_book"
    df = df.drop(columns=["raw_response"])
    return df


def build_frame(runs_dir: Path) -> pd.DataFrame:
    frames = []
    for folder in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        if folder.name in EXCLUDED_FOLDERS:
            print(f"  EXCLUDE {folder.name}: {EXCLUDED_FOLDERS[folder.name]}")
            continue
        df = load_run_folder(folder)
        if df is not None:
            frames.append(df)
            print(f"  OK {folder.name}: {len(df)} rows")
    if not frames:
        raise SystemExit(f"No usable run folders under {runs_dir}")

    full = pd.concat(frames, ignore_index=True)

    # Drop individually excluded riddles (see EXCLUDED_RIDDLES).
    if EXCLUDED_RIDDLES:
        excluded = full["riddle_id"].isin(EXCLUDED_RIDDLES)
        if excluded.any():
            n_rows = int(excluded.sum())
            n_riddles = full.loc[excluded, "riddle_id"].nunique()
            full = full[~excluded].reset_index(drop=True)
            for rid, reason in EXCLUDED_RIDDLES.items():
                print(f"  EXCLUDE riddle {rid}: {reason}")
            print(f"  ({n_rows} rows across {n_riddles} riddle(s) dropped)")

    # Model identity: (model_name, reasoning_mode). Display name appends the
    # reasoning mode only when needed to disambiguate.
    full["reasoning_mode"] = full["reasoning_mode"].fillna("none")
    key = full["model_name"] + " [" + full["reasoning_mode"] + "]"
    name_modes = full.groupby("model_name")["reasoning_mode"].nunique()
    ambiguous = set(name_modes[name_modes > 1].index)
    full["model_display"] = full["model_name"].where(
        ~full["model_name"].isin(ambiguous), key
    )

    # One run folder per model identity, else two runs would silently mix.
    folders_per_model = full.groupby(key)["source_folder"].nunique()
    dupes = folders_per_model[folders_per_model > 1]
    if not dupes.empty:
        detail = full[full["model_name"].isin(
            {k.split(" [")[0] for k in dupes.index}
        )].groupby(["model_name", "reasoning_mode"])["source_folder"].unique()
        raise SystemExit(
            "Model identity collision, same (model_name, reasoning_mode) in "
            f"multiple folders:\n{detail}"
        )

    return full


def load_judge_outputs(evals_outputs_dir: Path) -> pd.DataFrame:
    """Load heuristic judge outputs from evals/outputs/<run_id>/ folders.

    The judge writes one folder per run_id; rows key on riddle_id, which is
    unique within a run (one condition in v0). Join key: (run_id, riddle_id).
    """
    frames = []
    for folder in sorted(p for p in evals_outputs_dir.iterdir() if p.is_dir()):
        match_path = folder / "heuristic_match.jsonl"
        if not match_path.exists():
            continue
        rows = []
        with open(match_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                rows.append(
                    {
                        "run_id": folder.name,
                        "riddle_id": r.get("riddle_id"),
                        "judge_candidate": r.get("candidate"),
                        "judge_parse_status": r.get("parse_status"),
                        "judge_match": r.get("match"),
                        "judge_match_type": r.get("match_type"),
                        "judge_score": r.get("score"),
                        "judge_verdict": r.get("verdict"),
                    }
                )
        frames.append(pd.DataFrame(rows))
    if not frames:
        return pd.DataFrame(
            columns=["run_id", "riddle_id", "judge_candidate", "judge_parse_status",
                     "judge_match", "judge_match_type", "judge_score", "judge_verdict"]
        )
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    runs_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/responses_v0")
    out_path = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else Path("data/processed/results_tidy.parquet")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading runs from {runs_dir}")
    df = build_frame(runs_dir)

    evals_dir = Path(__file__).resolve().parents[2] / "evals" / "outputs"
    if evals_dir.is_dir():
        judge = load_judge_outputs(evals_dir)
        # A judge output folder is named after ONE run_id, but resumed runs
        # carry multiple run_ids in a single results file. Map judge folders
        # to source folders via run_id, then join on (source_folder,
        # riddle_id), which is unique per folder.
        run_to_folder = (
            df[["run_id", "source_folder"]]
            .drop_duplicates()
            .set_index("run_id")["source_folder"]
        )
        judge["source_folder"] = judge["run_id"].map(run_to_folder)
        unmapped = judge["source_folder"].isna()
        if unmapped.any():
            skipped = judge.loc[unmapped, "run_id"].nunique()
            judge = judge[~unmapped]
            print(f"  (ignored {skipped} judge folders not matching any loaded run)")
        judge = judge.drop(columns=["run_id"])
        before = len(df)
        df = df.merge(judge, on=["source_folder", "riddle_id"], how="left")
        assert len(df) == before, "judge merge changed row count, join key not unique"
        missing = df["judge_score"].isna().sum()
        print(f"\nJudge outputs merged from {evals_dir}")
        print(f"  rows without judge score: {missing}")
    else:
        print(f"\nNo judge outputs at {evals_dir}, skipping merge")

    print("\nSummary")
    print(f"  rows: {len(df)}")
    print(f"  models: {df['model_display'].nunique()}")
    print(f"  communities: {df['instance_community'].nunique()}")
    print(f"  conditions: {df['condition_id'].nunique()}")
    print("\nParse status counts:")
    print(df["answer_parse_status"].value_counts().to_string())
    if "judge_verdict" in df.columns:
        print("\nJudge verdict counts:")
        print(df["judge_verdict"].value_counts(dropna=False).to_string())
    print("\nRows per model:")
    print(df["model_display"].value_counts().to_string())

    try:
        df.to_parquet(out_path, index=False)
    except ImportError:
        out_path = out_path.with_suffix(".csv")
        df.to_csv(out_path, index=False)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
