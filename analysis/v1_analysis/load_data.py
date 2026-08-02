from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import pandas as pd

from text_features import (
    NEAR_DUPLICATE_OVERLAP_THRESHOLD,
    DUPLICATE_OVERLAP_THRESHOLD,
    LOW_FILL_EXCLUSION_THRESHOLD,
    clean_topic_label,
    community_token_from_filename,
    is_wildcard_topic,
    jaccard_overlap,
    normalize_answer_text,
    normalize_columns,
    strip_phantom_rows,
)

DEFAULT_INPUT_DIR = Path.home() / "Downloads" / "v1"
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "csv"
REFERENCE_SHEET_NAME = "reference_sheet.xlsx"


def discover_workbooks(input_dir: Path) -> list[Path]:
    files = [
        p
        for p in sorted(input_dir.glob("*.xlsx"))
        if not p.name.startswith("~$") and p.name != REFERENCE_SHEET_NAME
    ]
    return files


def load_workbook(path: Path) -> tuple[pd.DataFrame, dict]:
    xl = pd.ExcelFile(path)
    sheet_used = "Riddles" if "Riddles" in xl.sheet_names else xl.sheet_names[0]
    raw = pd.read_excel(xl, sheet_name=sheet_used)
    raw = strip_phantom_rows(normalize_columns(raw))
    community = community_token_from_filename(path.name)
    raw.insert(0, "source_file", path.name)
    raw.insert(1, "community", community)
    meta = {
        "file": path.name,
        "community": community,
        "sheet_names": xl.sheet_names,
        "sheet_used": sheet_used,
        "used_fallback_sheet": sheet_used != "Riddles",
        "n_filled_rows": len(raw),
    }
    return raw, meta


def resolve_duplicates(
    frames: dict[str, list[tuple[Path, pd.DataFrame]]],
    quality_notes: list[dict],
) -> dict[str, pd.DataFrame]:
    resolved: dict[str, pd.DataFrame] = {}
    for community, entries in frames.items():
        if len(entries) == 1:
            resolved[community] = entries[0][1]
            continue

        entries_sorted = sorted(entries, key=lambda e: ("(" in e[0].stem, e[0].name))
        kept: list[tuple[Path, pd.DataFrame]] = [entries_sorted[0]]
        for path, df in entries_sorted[1:]:
            kept_path, kept_df = kept[0]
            overlap = jaccard_overlap(
                set(kept_df["riddle_english"].dropna().map(normalize_answer_text)),
                set(df["riddle_english"].dropna().map(normalize_answer_text)),
            )
            if overlap >= DUPLICATE_OVERLAP_THRESHOLD:
                quality_notes.append(
                    {
                        "issue": "duplicate_submission_dropped",
                        "community": community,
                        "detail": f"{path.name} overlaps {overlap:.0%} with {kept_path.name}; dropped {path.name}",
                    }
                )
            else:
                suffix_community = f"{community}__alt{len(kept)}"
                df = df.copy()
                df["community"] = suffix_community
                quality_notes.append(
                    {
                        "issue": "unresolved_community_collision",
                        "community": community,
                        "detail": (
                            f"{path.name} only overlaps {overlap:.0%} with {kept_path.name} "
                            f"under the same community name; kept separately as {suffix_community}"
                        ),
                    }
                )
                resolved[suffix_community] = df

        resolved[community] = kept[0][1]
    return resolved


def detect_near_duplicate_communities(consolidated: pd.DataFrame) -> pd.DataFrame:
    text_sets = {
        community: set(group["riddle_english"].dropna().map(normalize_answer_text))
        for community, group in consolidated.groupby("community")
    }
    authors = {
        community: set(group["author_credit"].dropna().astype(str))
        for community, group in consolidated.groupby("community")
    }

    rows = []
    for community_a, community_b in combinations(sorted(text_sets), 2):
        overlap = jaccard_overlap(text_sets[community_a], text_sets[community_b])
        if overlap < NEAR_DUPLICATE_OVERLAP_THRESHOLD:
            continue
        shared_authors = authors[community_a] & authors[community_b]
        rows.append(
            {
                "community_a": community_a,
                "community_b": community_b,
                "riddle_text_overlap": round(overlap, 3),
                "shared_authors": "; ".join(sorted(shared_authors)) if shared_authors else "",
            }
        )
    return pd.DataFrame(rows).sort_values("riddle_text_overlap", ascending=False) if rows else pd.DataFrame(
        columns=["community_a", "community_b", "riddle_text_overlap", "shared_authors"]
    )


def build_consolidated_dataset(
    input_dir: Path, output_dir: Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    quality_notes: list[dict] = []
    frames: dict[str, list[tuple[Path, pd.DataFrame]]] = {}

    for path in discover_workbooks(input_dir):
        df, meta = load_workbook(path)
        if meta["n_filled_rows"] < LOW_FILL_EXCLUSION_THRESHOLD:
            quality_notes.append(
                {
                    "issue": "excluded_low_fill",
                    "community": meta["community"],
                    "detail": f"{path.name} has only {meta['n_filled_rows']} filled riddle rows; excluded",
                }
            )
            continue
        if meta["used_fallback_sheet"]:
            quality_notes.append(
                {
                    "issue": "fallback_sheet_used",
                    "community": meta["community"],
                    "detail": f"{path.name} has no 'Riddles' worksheet; used '{meta['sheet_used']}' instead",
                }
            )
        frames.setdefault(meta["community"], []).append((path, df))

    resolved = resolve_duplicates(frames, quality_notes)
    consolidated = pd.concat(resolved.values(), ignore_index=True)

    english_original_mask = consolidated["community"].str.lower().str.startswith("english_")
    for english_col, original_col, label in [
        ("riddle_english", "riddle_original", "'Riddle (English Translation)'"),
        ("reference_answer_english", "reference_answer_original", "'Reference Answer (English)'"),
    ]:
        was_blank_mask = english_original_mask & consolidated[english_col].isna()
        consolidated.loc[english_original_mask, english_col] = consolidated.loc[
            english_original_mask, english_col
        ].fillna(consolidated.loc[english_original_mask, original_col])
        n_backfilled = int(was_blank_mask.sum())
        if n_backfilled:
            quality_notes.append(
                {
                    "issue": "english_translation_backfilled_from_original",
                    "community": "English_*",
                    "detail": (
                        f"{n_backfilled} rows in English-original communities had a blank "
                        f"{label} column; filled from the Original-language column "
                        "since it is already English"
                    ),
                }
            )

    consolidated["topic_raw"] = consolidated["topic"]
    consolidated["is_wildcard"] = consolidated["topic_raw"].map(is_wildcard_topic)
    consolidated["wildcard_topic"] = consolidated["topic_raw"].where(
        ~consolidated["is_wildcard"], consolidated["topic_raw"].map(clean_topic_label)
    )
    consolidated.loc[~consolidated["is_wildcard"], "wildcard_topic"] = pd.NA

    near_dupes = detect_near_duplicate_communities(consolidated)
    for _, row in near_dupes.iterrows():
        quality_notes.append(
            {
                "issue": "near_duplicate_community_pair",
                "community": f"{row['community_a']} / {row['community_b']}",
                "detail": (
                    f"riddle-text overlap {row['riddle_text_overlap']:.0%}"
                    + (f"; shared authors: {row['shared_authors']}" if row["shared_authors"] else "")
                ),
            }
        )

    quality_df = pd.DataFrame(quality_notes)
    near_dupes.to_csv(output_dir / "near_duplicate_community_pairs.csv", index=False)
    return consolidated, quality_df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    consolidated, quality_df = build_consolidated_dataset(args.input_dir, args.output_dir)

    consolidated.to_csv(args.output_dir / "riddles_v1_consolidated.csv", index=False)
    quality_df.to_csv(args.output_dir / "data_quality_notes.csv", index=False)

    print(f"communities: {consolidated['community'].nunique()}")
    print(f"riddles: {len(consolidated)}")
    print(f"quality notes: {len(quality_df)}")


if __name__ == "__main__":
    main()
