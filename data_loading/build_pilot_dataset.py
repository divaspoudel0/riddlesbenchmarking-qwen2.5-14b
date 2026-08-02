"""Build the pilot dataset v1 for the framework team.

Consolidates all passing JSONL submissions into a single JSONL file
mapped to the Analysis team's canonical instance schema. Performs a
script-family sanity check to catch obvious language-code
mismatches at build time.

Usage:
    uv run python build_pilot_dataset.py

Inputs:
    reports/passed_jsonl/*.jsonl    (output of validate_submissions.py)

Outputs:
    pilot_dataset/pilot_dataset_v1.jsonl
    pilot_dataset/README.md
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pilot_dataset_config import (
    DEFAULT_SCRIPT_FAMILY,
    ISO_TO_SCRIPT_FAMILY,
    LANGUAGE_TO_ISO_639_2,
    SCHEMA_FIELD_ORDER,
    STANDARD_TOPICS,
    TEMPLATE_TO_CANONICAL,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE = Path(__file__).parent

# Each run batch has its own validated output directory. The build reads
# from these in order; when a community appears in more than one batch the
# later batch wins (a corrected v0 community re-submitted in v1 is bumped to
# v1, so a v1-only eval run correctly re-runs it).
RUN_BATCH_DIRS = {
    "v0": HERE / "reports" / "passed_jsonl",
    "v1": HERE / "reports_v1" / "passed_jsonl",
    "v2": HERE / "reports_v2" / "passed_jsonl",
}
DEFAULT_BATCH_ORDER = ["v0", "v1", "v2"]

OUTPUT_DIR = HERE / "pilot_dataset"
OUTPUT_FILE = OUTPUT_DIR / "pilot_dataset_v1.jsonl"
README_FILE = OUTPUT_DIR / "README.md"


# ---------------------------------------------------------------------------
# Unicode script detection (Option A)
# ---------------------------------------------------------------------------
def detect_script_family(text: str) -> str:
    """Return the dominant Unicode script family in a string.

    Looks at character ranges and counts which script appears most often.
    Returns one of: arabic, han, cyrillic, devanagari, bengali, tamil,
    telugu, kannada, malayalam, thai, latin, unknown.
    """
    if not text:
        return "unknown"

    counts: Counter[str] = Counter()
    for ch in text:
        cp = ord(ch)
        if 0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F:
            counts["arabic"] += 1
        elif 0x4E00 <= cp <= 0x9FFF:
            counts["han"] += 1
        elif 0x0400 <= cp <= 0x04FF:
            counts["cyrillic"] += 1
        elif 0x0900 <= cp <= 0x097F:
            counts["devanagari"] += 1
        elif 0x0980 <= cp <= 0x09FF:
            counts["bengali"] += 1
        elif 0x0B80 <= cp <= 0x0BFF:
            counts["tamil"] += 1
        elif 0x0C00 <= cp <= 0x0C7F:
            counts["telugu"] += 1
        elif 0x0C80 <= cp <= 0x0CFF:
            counts["kannada"] += 1
        elif 0x0D00 <= cp <= 0x0D7F:
            counts["malayalam"] += 1
        elif 0x0E00 <= cp <= 0x0E7F:
            counts["thai"] += 1
        elif 0x0041 <= cp <= 0x007A:
            counts["latin"] += 1

    if not counts:
        return "unknown"
    return counts.most_common(1)[0][0]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def slugify(text: str) -> str:
    """Lowercase, replace non-alphanumeric runs with underscores."""
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)


def parse_community_from_filename(filename: str) -> str:
    """Extract community token from validator's JSONL filename.

    Files are named like:
        cultural_riddles_benchmark_tamil_india.jsonl
    Returns "tamil_india".
    """
    stem = Path(filename).stem
    return stem.replace("cultural_riddles_benchmark_", "")


def map_language(community: str) -> str:
    """Map community token to a single ISO 639-2/3 code.

    Per the project metadata spec, each riddle has exactly one language
    code. Lookup strategy:
      1. Try the full community key (e.g. "arabic_egypt" -> "arz").
         This is needed for languages whose dialect depends on country
         (Arabic varieties especially).
      2. Fall back to the first underscore-separated token
         (e.g. "tamil_india" -> "tamil" -> "tam"). This is the
         common case for monolithic languages.
    """
    community_lower = community.lower()

    iso = LANGUAGE_TO_ISO_639_2.get(community_lower)
    if iso is not None:
        return iso

    first_token = community_lower.split("_")[0]
    iso = LANGUAGE_TO_ISO_639_2.get(first_token)
    if iso is None:
        raise ValueError(
            f"Unknown language token {first_token!r} in community "
            f"{community!r}. Add it to LANGUAGE_TO_ISO_639_2."
        )
    return iso


def is_wildcard_topic(topic: str | None) -> bool:
    """A topic is a wildcard if it's not in the 8 standard topics."""
    if topic is None:
        return False
    return topic not in STANDARD_TOPICS


def build_riddle_id(community: str, topic: str | None, number: int | None) -> str:
    """Construct stable, sortable riddle ID.

    Format: {community_lower}_{topic_slug}_{number_padded_3}
    Example: tamil_india_history_007
    """
    community_part = community.lower()
    topic_part = slugify(topic) if topic else "unknown"
    number_part = f"{number:03d}" if number is not None else "000"
    return f"{community_part}_{topic_part}_{number_part}"


def transform_record(
    raw: dict,
    community: str,
    language_iso: str,
    created_at: str,
    run_batch: str,
) -> dict:
    """Convert one raw JSONL record into a canonical-schema record."""
    # Pull renamed fields
    canonical: dict = {
        TEMPLATE_TO_CANONICAL[k]: v
        for k, v in raw.items()
        if k in TEMPLATE_TO_CANONICAL
    }

    # Preserve everything else (including extra columns like custom scripts)
    raw_template = {
        k: v for k, v in raw.items() if k not in TEMPLATE_TO_CANONICAL
    }

    # Build identifiers
    number = canonical.get("source_row_number")
    try:
        number_int = int(number) if number is not None else None
    except (TypeError, ValueError):
        # Some files use strings like "Tel 042" — strip non-digits
        digits = re.findall(r"\d+", str(number))
        number_int = int(digits[0]) if digits else None

    topic = canonical.get("topic")
    riddle_id = build_riddle_id(community, topic, number_int)

    # Assemble final record in canonical field order
    record = {
        "instance_result_id": str(uuid.uuid4()),
        "riddle_id": riddle_id,
        "created_at": created_at,
        "source_row_number": number_int,
        "language": language_iso,
        "community": community,
        "run_batch": run_batch,
        "topic": topic,
        "is_wildcard": is_wildcard_topic(topic),
        "riddle_original": canonical.get("riddle_original"),
        "riddle_english": canonical.get("riddle_english"),
        "reference_answer_original": canonical.get("reference_answer_original"),
        "reference_answer_english": canonical.get("reference_answer_english"),
        "riddle_hint": canonical.get("riddle_hint"),
        "riddle_note": canonical.get("riddle_note"),
        "author_credit": canonical.get("author_credit"),
        "human_validator_name": canonical.get("human_validator_name"),
        "human_answer_original": canonical.get("human_answer_original"),
        "human_answer_score": canonical.get("human_answer_score"),
        "human_answer_comment": canonical.get("human_answer_comment"),
        "row_status": "valid",
        "raw_template_fields": raw_template,
    }

    # Re-order according to SCHEMA_FIELD_ORDER (any unlisted fields go last)
    ordered = {k: record[k] for k in SCHEMA_FIELD_ORDER if k in record}
    for k, v in record.items():
        if k not in ordered:
            ordered[k] = v

    return ordered


def script_check(records: list[dict], community: str, primary_iso: str) -> str | None:
    """Sample riddle text and compare detected vs expected script family.

    Returns a warning string if mismatch detected, None if OK.
    """
    sample_text = " ".join(
        str(r.get("riddle_original", "")) for r in records[:20] if r.get("riddle_original")
    )
    if not sample_text.strip():
        return None

    detected = detect_script_family(sample_text)
    expected = ISO_TO_SCRIPT_FAMILY.get(primary_iso, DEFAULT_SCRIPT_FAMILY)

    if detected == expected:
        return None
    if detected == "unknown":
        return None  # short or unusual content; don't false-alarm

    return (
        f"    {community}: expected {expected!r} script for ISO {primary_iso!r}, "
        f"but riddles look like {detected!r}. Verify language code in config."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(batches: list[str], output_dir: Path) -> None:
    created_at = datetime.now(timezone.utc).isoformat()

    # community -> {records, run_batch, language, count}. Later batch overrides.
    community_data: dict[str, dict] = {}
    warnings: list[str] = []

    for batch in batches:
        passed_dir = RUN_BATCH_DIRS.get(batch)
        if passed_dir is None:
            raise SystemExit(
                f"Unknown batch {batch!r}. Known batches: {list(RUN_BATCH_DIRS)}"
            )
        if not passed_dir.exists():
            print(f"  [skip] batch {batch}: {passed_dir} not found")
            continue

        jsonl_files = sorted(passed_dir.glob("*.jsonl"))
        print(
            f"Batch {batch}: {len(jsonl_files)} passing submissions "
            f"({passed_dir.relative_to(HERE)})"
        )

        for jsonl_path in jsonl_files:
            community = parse_community_from_filename(jsonl_path.name)
            try:
                language_iso = map_language(community)
            except ValueError as exc:
                warnings.append(f"   {community}: {exc}")
                continue

            raw_records = []
            with jsonl_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        raw_records.append(json.loads(line))

            transformed = [
                transform_record(r, community, language_iso, created_at, batch)
                for r in raw_records
            ]

            warning = script_check(raw_records, community, language_iso)
            if warning:
                warnings.append(warning)

            if community in community_data:
                print(
                    f"    [override] {community}: re-submitted in {batch}, "
                    f"replacing batch {community_data[community]['run_batch']}"
                )

            community_data[community] = {
                "records": transformed,
                "run_batch": batch,
                "language": language_iso,
                "count": len(transformed),
            }

    if not community_data:
        raise SystemExit(
            "No passing submissions found in any batch. "
            "Run `uv run python validate_submissions.py` first."
        )

    # Flatten in deterministic community order
    all_records: list[dict] = []
    per_community_counts: dict[str, int] = {}
    for community in sorted(community_data):
        data = community_data[community]
        all_records.extend(data["records"])
        per_community_counts[community] = data["count"]

    output_dir.mkdir(exist_ok=True)
    out_file = output_dir / OUTPUT_FILE.name
    with out_file.open("w", encoding="utf-8") as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    write_readme(community_data, len(all_records), created_at, batches)
    registry_path = write_registry(
        community_data, batches, created_at, output_dir, len(all_records)
    )

    print()
    print(
        f"Consolidated {len(per_community_counts)} communities, "
        f"{len(all_records)} riddles across batches: {', '.join(batches)}."
    )
    print(f"   Output:   {out_file.relative_to(HERE)}")
    print(f"   README:   {README_FILE.relative_to(HERE)}")
    print(f"   Registry: {registry_path.relative_to(HERE)}")

    if warnings:
        print()
        print("Warnings:")
        for w in warnings:
            print(w)
    else:
        print()
        print("No language-script mismatches detected.")


def write_readme(
    community_data: dict[str, dict],
    total: int,
    created_at: str,
    batches: list[str],
) -> None:
    """Document the pilot dataset for downstream consumers."""
    lines = [
        "# Pilot Dataset v1",
        "",
        f"Generated: {created_at}",
        f"Total submissions: {len(community_data)}",
        f"Total riddles: {total}",
        f"Run batches: {', '.join(batches)}",
        "",
        "> **Naming note.** The `v1` in the filename `pilot_dataset_v1.jsonl` is the",
        "> dataset *schema* version; it becomes v2 when `raw_template_fields` is",
        "> dropped. The `v1` in the `run_batch` field is a *collection round*, the",
        "> second wave of communities. These are separate axes. To evaluate only the",
        "> newly added communities, select by `run_batch` (the eval CLI's",
        "> `--run-batch` flag), not by the filename. See Versioning below.",
        "",
        "## Purpose",
        "",
        "First consolidated dataset for the framework team (T2.2.1).",
        "Includes only submissions that passed all validator blocking checks.",
        "Schema follows the Analysis team's canonical instance schema.",
        "Combines all run batches into one dataset; each riddle is tagged with",
        "its `run_batch` so evaluation runs can target only new or changed",
        "communities. See Versioning below.",
        "",
        "## Schema",
        "",
        "Each line is one riddle as a JSON object. Fields:",
        "",
        "| Field | Type | Description |",
        "|---|---|---|",
        "| `instance_result_id` | string (UUID v4) | Unique per row |",
        "| `riddle_id` | string | Stable structured ID: `{community}_{topic}_{number}` |",
        "| `created_at` | ISO 8601 | When this dataset was built |",
        "| `source_row_number` | int | Original row number in contributor's spreadsheet |",
        "| `language` | string (ISO 639-2/3) | Language code, per project metadata spec |",
        "| `community` | string | Community token (e.g. `tamil_india`) |",
        "| `run_batch` | string | Submission batch this community entered or was last changed in (`v0`, `v1`, ...). Internal; dropped from the HuggingFace release. |",
        "| `topic` | string | Topic name as submitted |",
        "| `is_wildcard` | bool | True if topic is community-specific, not one of the 8 standard topics |",
        "| `riddle_original` | string | Riddle text in source language |",
        "| `riddle_english` | string | English translation |",
        "| `reference_answer_original` | string | Reference answer in source language |",
        "| `reference_answer_english` | string | Reference answer in English |",
        "| `riddle_hint` | string or null | Optional hint |",
        "| `riddle_note` | string or null | Optional comment about region/generation specificity |",
        "| `author_credit` | string or null | Submitter name |",
        "| `human_validator_name` | string or null | Person who scored the human answer |",
        "| `human_answer_original` | string or null | Human evaluator's answer attempt |",
        "| `human_answer_score` | string or null | 0-2 rating (raw label from spreadsheet) |",
        "| `human_answer_comment` | string or null | Comment on the human answer |",
        "| `row_status` | string | `\"valid\"` for all rows in v1 |",
        "| `raw_template_fields` | object | Original column names → values, for any field not in canonical schema. Dropped in v2. |",
        "",
        "## Coverage",
        "",
        "| Community | Batch | Riddles |",
        "|---|---|---|",
    ]
    for community in sorted(community_data):
        data = community_data[community]
        lines.append(f"| `{community}` | {data['run_batch']} | {data['count']} |")

    lines += [
        "",
        "## Design decisions",
        "",
        "- **Anti-corruption layer**: contributors write to the template schema;",
        "  this script transforms once at the boundary to canonical schema. Single",
        "  point of truth, no per-team conversion drift.",
        "- **ISO 639-2/3 language codes**: matches Analysis team's instance schema.",
        "  Arabic dialects use 639-3 codes (`arz`, `apd`, `apc`, `ary`); macro-language",
        "  `ara` would lose dialect information critical to a cultural benchmark.",
        "- **Verified language codes by source inspection**: Egyptian, Sudanese,",
        "  Syrian, Moroccan, Cantonese, Mongondow language codes were confirmed by",
        "  reading actual riddle content rather than guessing from filenames.",
        "  (Sudanese was initially mismapped to Sundanese before verification.)",
        "- **Script-family sanity check**: build runs a Unicode block check against",
        "  the expected script family. Warnings printed but don't block the build.",
        "- **`raw_template_fields` nested object**: preserves any column not in",
        "  the canonical mapping (e.g. custom transliteration columns some",
        "  contributors added). Allows v1 consumers to recover original data if",
        "  needed. Dropped in v2 once mappings are validated.",
        "- **Structured `riddle_id`**: stable across rebuilds, human-readable,",
        "  sortable by community → topic → number.",
        "",
        "## Open questions",
        "",
        "1. **English + hints condition**: hints are written in source language",
        "   only. Should hints be translated for the English condition, or",
        "   fed mixed-language?",
        "2. **`human_answer_score` field**: kept as raw string label (e.g.",
        "   `\"2: correct\"`) for v1 because contributor files use inconsistent",
        "   formats. Should be parsed to int 0/1/2 in v2.",
        "3. **Scoring scale mismatch**: contributor template uses a 0-2 scale",
        "   for `Rating of Human Answer`, while the project metadata schema",
        "   and aggregate metrics use a 0-3 scale (0=hallucination, 1=honest",
        "   uncertainty, 2=partial, 3=correct). Needs reconciliation before",
        "   benchmarking starts.",
        "",
        "## How to rebuild",
        "",
        "```bash",
        "cd data_loading",
        "# validate each batch into its own reports directory",
        "uv run python validate_submissions.py --run-batch v0 --no-download",
        "uv run python validate_submissions.py --run-batch v1 --no-download",
        "# combine all batches into the dataset + registry",
        "uv run python build_pilot_dataset.py",
        "# or build a single batch:",
        "uv run python build_pilot_dataset.py --batches v1",
        "```",
        "",
        "## Versioning",
        "",
        "Two independent version axes. Do not conflate them.",
        "",
        "### Run batches",
        "",
        "Communities are grouped into run batches: `v0` is the original",
        "collection, `v1` the next round, and so on. Every riddle carries a",
        "`run_batch` tag, and the build also writes `submission_registry.yaml`,",
        "a per-community manifest of language, run_batch, and riddle count.",
        "",
        "The registry is the human-readable manifest of which community is in",
        "which batch. Model runs are self-funded, so teams should not re-pay to",
        "evaluate communities they already ran. Each riddle carries its",
        "`run_batch`, and the eval CLI filters on it: pass `--run-batch v1` to",
        "cover only the new and corrected communities, or omit the flag to run",
        "all batches when bringing a new model online. A community that is",
        "corrected and re-submitted in a later batch is bumped to that batch, so",
        "a `--run-batch v1` run correctly re-runs it.",
        "",
        "### Schema versions",
        "",
        "- **v1** (this version): includes `raw_template_fields` for forward",
        "  compatibility. Analysis team consumes canonical fields; data preserved",
        "  for review.",
        "- **v2** (planned): drops `raw_template_fields` after Analysis confirms",
        "  the mapping is complete. May parse `human_answer_score` to int and",
        "  reconcile the 0-2 vs 0-3 scoring scale mismatch.",
    ]

    README_FILE.write_text("\n".join(lines), encoding="utf-8")


def write_registry(
    community_data: dict[str, dict],
    batches: list[str],
    created_at: str,
    output_dir: Path,
    total_riddles: int,
) -> Path:
    """Write the submission registry YAML: the source of truth for delta runs.

    One entry per community with its language code, run batch, and riddle
    count. The eval CLI reads this to resolve which communities belong to a
    given batch, so a v1-only run can skip the v0 communities that were
    already evaluated. Regenerated on every build; do not hand-edit.
    """
    registry_path = output_dir / "submission_registry.yaml"
    lines = [
        "# Auto-generated by build_pilot_dataset.py. Do not edit by hand.",
        "# Source of truth for run-batch delta runs: the eval CLI reads this to",
        "# decide which communities to run for a given batch. Rerun the build to",
        "# regenerate.",
        "metadata:",
        f"  generated: {created_at}",
        f"  batches: [{', '.join(batches)}]",
        f"  total_communities: {len(community_data)}",
        f"  total_riddles: {total_riddles}",
        "communities:",
    ]
    for community in sorted(community_data):
        data = community_data[community]
        lines.append(f"  {community}:")
        lines.append(f"    language: {data['language']}")
        lines.append(f"    run_batch: {data['run_batch']}")
        lines.append(f"    riddles: {data['count']}")
    registry_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return registry_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the combined pilot dataset from one or more run batches. "
            "Batches are read in order; a later batch overrides an earlier one "
            "for the same community."
        )
    )
    parser.add_argument(
        "--batches",
        nargs="+",
        choices=list(RUN_BATCH_DIRS),
        default=DEFAULT_BATCH_ORDER,
        help=(
            "Run batches to include, in precedence order (later wins). "
            f"Default: {' '.join(DEFAULT_BATCH_ORDER)}."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for the built dataset (default: pilot_dataset/).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.batches, args.output_dir)