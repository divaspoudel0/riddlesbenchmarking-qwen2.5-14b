"""Export the pilot dataset to a HuggingFace-ready dataset (parquet + card).

Reads the validated pilot dataset and writes a clean parquet with only the
public columns, plus a dataset card (README.md). Drops internal fields
(instance_result_id, created_at, source_row_number, raw_template_fields,
row_status) and the deprecated human_* validation fields (the v2 contribution
format no longer collects them). The internal `run_batch` is kept but renamed
to the public-facing `release_version`. Output goes to hf_export/ for upload.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
DEFAULT_INPUT = HERE / "pilot_dataset" / "pilot_dataset_v1.jsonl"
DEFAULT_OUTPUT_DIR = HERE / "hf_export"

REPO_ID = "CohereLabsCommunity/multicultural-riddles-benchmark"
PRETTY_NAME = "Multicultural Riddles Benchmark"

# Source column -> public column name. Order here is the output column order.
COLUMN_MAP = {
    "riddle_id": "riddle_id",
    "language": "language",
    "community": "community",
    "run_batch": "release_version",
    "topic": "topic",
    "is_wildcard": "is_wildcard",
    "riddle_original": "riddle_original",
    "riddle_english": "riddle_english",
    "reference_answer_original": "reference_answer_original",
    "reference_answer_english": "reference_answer_english",
    "riddle_hint": "riddle_hint",
    "riddle_note": "riddle_note",
    "author_credit": "author_credit",
}
SOURCE_COLUMNS = list(COLUMN_MAP.keys())
PUBLIC_COLUMNS = list(COLUMN_MAP.values())

REQUIRED_NON_NULL = [
    "riddle_id",
    "language",
    "community",
    "release_version",
    "topic",
    "is_wildcard",
    "riddle_original",
    "reference_answer_original",
    "author_credit",
]

FIELD_DESCRIPTIONS = [
    ("riddle_id", "string", "Stable unique id, `{community}_{topic}_{number}`."),
    ("language", "string", "ISO 639-3 code of the riddle's language."),
    ("community", "string", "Cultural community, `{culture}_{country}` (e.g. `tamil_india`)."),
    ("release_version", "string", "Collection round the community was added in (`v0`, `v1`, ...)."),
    ("topic", "string", "Topic category the riddle belongs to."),
    ("is_wildcard", "bool", "True if the riddle is from a community-chosen wildcard topic."),
    ("riddle_original", "string", "The riddle in its original language."),
    ("riddle_english", "string", "English translation of the riddle. Reference only; may be null."),
    ("reference_answer_original", "string", "Gold answer in the original language."),
    ("reference_answer_english", "string", "English translation of the answer. May be null."),
    ("riddle_hint", "string", "Optional hint. May be null."),
    ("riddle_note", "string", "Optional note or comment from the author. May be null."),
    ("author_credit", "string", "Contributor(s) who wrote the riddle."),
]


def load_rows(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_public_frame(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in SOURCE_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"Source is missing expected columns: {missing}")

    public = df[SOURCE_COLUMNS].rename(columns=COLUMN_MAP).copy()

    # Coerce text columns to string (some numeric answers are stored as ints).
    # pd.isna catches None and NaN, so real nulls and empty strings become None,
    # never the literal text "nan". is_wildcard stays boolean.
    string_columns = [c for c in PUBLIC_COLUMNS if c != "is_wildcard"]
    for col in string_columns:
        public[col] = public[col].apply(
            lambda v: None if (pd.isna(v) or v == "") else str(v)
        )
    public["is_wildcard"] = public["is_wildcard"].astype(bool)

    problems = []
    for col in REQUIRED_NON_NULL:
        n_null = int(public[col].isna().sum())
        if n_null:
            problems.append(f"{col}: {n_null} null")
    if problems:
        raise SystemExit("Required columns have nulls:\n  " + "\n  ".join(problems))
    return public


def parse_contributors(df: pd.DataFrame) -> dict[str, list[str]]:
    """Best-effort per-community contributor lists from author_credit.

    The source field is inconsistent (comma/slash/newline joined, parenthetical
    notes, source tags, case duplicates), so the result is provisional and the
    card marks it as pending contributor confirmation.
    """
    def clean_name(nm: str) -> str:
        nm = re.sub(r"\([^)]*\)", "", nm)
        nm = re.sub(r"\[[^\]]*\]", "", nm)
        nm = nm.replace("`", "").strip()
        nm = re.sub(r"\s+", " ", nm)
        return nm.strip(" ,/")

    def split_names(cell: str) -> list[str]:
        cell = cell.replace("\n", ",")
        return [clean_name(p) for p in re.split(r",|;|/|\s+and\s+|\s*&\s*", cell) if clean_name(p)]

    def is_concat(name: str, names: set[str]) -> bool:
        # True if `name` is just a space-join of two or more other names in the
        # same community (a data-entry artifact, e.g. one cell that wrote two
        # authors with a space instead of a comma).
        words = name.split()
        others = names - {name}

        def cover(start: int, used: int) -> bool:
            if start == len(words):
                return used >= 2
            for end in range(start + 1, len(words) + 1):
                if " ".join(words[start:end]) in others and cover(end, used + 1):
                    return True
            return False

        return cover(0, 0)

    cells = collections.defaultdict(set)
    topics = collections.defaultdict(set)
    for _, r in df.iterrows():
        cells[r["community"]].add(str(r["author_credit"]).strip())
        topics[r["community"]].add(str(r["topic"]).strip().lower())

    per = {}
    for comm, cs in cells.items():
        names = {}
        for cell in cs:
            for nm in split_names(cell):
                k = nm.lower()
                if k not in names or (nm[:1].isupper() and not names[k][:1].isupper()):
                    names[k] = nm
        values = set(names.values())
        # Drop space-join artifacts and values that are actually a topic name
        # pasted into the author field.
        values = {n for n in values if not is_concat(n, values)}
        values = {n for n in values if n.lower() not in topics[comm]}
        per[comm] = sorted(values, key=str.lower)
    return per


def render_card(public: pd.DataFrame) -> str:
    languages = sorted(public["language"].unique())
    communities = sorted(public["community"].unique())
    n_rows = len(public)
    n_wild = int(public["is_wildcard"].sum())
    per = parse_contributors(public)

    lang_yaml = "\n".join(f"- {c}" for c in languages)
    fields_table = "| Field | Type | Description |\n|---|---|---|\n" + "\n".join(
        f"| `{n}` | {t} | {desc} |" for n, t, desc in FIELD_DESCRIPTIONS
    )
    credits = "\n".join(f"- **{c}**: {', '.join(per[c])}" for c in communities)

    return f"""---
license: cc-by-4.0
pretty_name: {PRETTY_NAME}
language:
{lang_yaml}
task_categories:
- question-answering
multilinguality:
- multilingual
size_categories:
- 1K<n<10K
annotations_creators:
- expert-generated
language_creators:
- expert-generated
source_datasets:
- original
tags:
- riddles
- cultural-reasoning
- cultural-knowledge
- multilingual
- multicultural
- community-curated
- low-resource-languages
configs:
- config_name: default
  data_files:
  - split: test
    path: data/test-*
---

# {PRETTY_NAME}

A community-built benchmark of original cultural riddles spanning **{len(communities)} communities across {len(languages)} languages**. Each riddle describes something without ever naming it, so answering it requires genuine cultural knowledge rather than translation or web search. A native speaker would recognise the answer instantly; a model only succeeds if it carries that culture's knowledge.

## Dataset summary

Most multilingual benchmarks are written in English and translated outward, which tests language but not culture. This benchmark inverts that. Native speakers from each community write their own riddles from scratch, using a shared English framework only as a starting point, not as a source to translate. The riddles are intentionally indirect: they use local nicknames, synonyms, and oblique description so that the answer cannot be reached by recognising a keyword. The goal is depth of cultural understanding, measured where today's models tend to be fluent but shallow.

This is the pilot release: **{n_rows} riddles** across {len(communities)} communities, of which {n_wild} come from community-chosen wildcard topics. It is intended for evaluation only.

## Why riddles

A riddle names nothing. "This red-crossed sphere's juice is not sweet for your stomach" means nothing to a search engine, but every Hungarian recognises Unicum, a famous bitters. A model that only knows the formal name misses it entirely. Because each riddle is original, unpublished, and culturally specific, it resists both memorisation and reverse-engineering from training data, which gives the benchmark a longer useful life than fact-lookup tasks.

## Languages and communities

The base unit is the present-day national-linguistic community, for example Spanish from Argentina or Bengali from India. {len(communities)} communities are represented across {len(languages)} languages. Languages outnumber communities because several communities share a language: Argentine, Cuban, and Peruvian riddles are all in Spanish but draw on three different cultures. That separation is the point of the benchmark.

The benchmark grows over time. Each community carries a `release_version` marking the collection round it entered in (`v0` is the first round, `v1` the next, and so on), so results can be compared across releases.

## Dataset structure

### Data fields

{fields_table}

### Splits

A single `test` split of {n_rows} rows. `community`, `language`, and `topic` are columns to filter on, not separate splits.

## Loading the dataset

```python
from datasets import load_dataset

ds = load_dataset("{REPO_ID}", split="test")

# filter to one community
tamil = ds.filter(lambda r: r["community"] == "tamil_india")

# filter to one language
egyptian_arabic = ds.filter(lambda r: r["language"] == "arz")
```

## Curation

Every riddle is original human writing. Contributors are native speakers who write for their own community, following a shared format of topics and questions per topic. AI tools may be used for brainstorming or to test how hard a riddle is for a model, but the riddles themselves are written by people, not generated. English translations are provided for human reference and documentation only, never to present the riddle to a model. All riddles are free of personally identifiable information.

## Intended use and terms

Released under **CC-BY-4.0**: you may share and adapt the data, including commercially, with attribution.

**This data must not be used to train, fine-tune, or distill models, nor as seeds for synthetic data generation.** It is an evaluation benchmark. Using it as training data defeats its purpose and contaminates future measurement. Please respect this restriction in addition to the license.

## Contributors

This benchmark was proposed by **Károly Boczka** and **Julia Kreutzer**, and built by native-speaker contributors across the Cohere Labs Community.

> Note: the per-community credits below are derived from contributor-supplied author fields and are provisional pending contributor confirmation before any public release.

{credits}

## Citation

```bibtex
@misc{{multicultural_riddles_2026,
  title        = {{{PRETTY_NAME}}},
  author       = {{Boczka, K{{\\'a}}roly and Kreutzer, Julia and the Cohere Labs Community}},
  year         = {{2026}},
  publisher    = {{Hugging Face}},
  howpublished = {{\\url{{https://huggingface.co/datasets/{REPO_ID}}}}}
}}
```
"""


def main(input_path: Path, output_dir: Path) -> None:
    if not input_path.exists():
        raise SystemExit(
            f"Input not found: {input_path}. Run build_pilot_dataset.py first."
        )

    df = pd.DataFrame(load_rows(input_path))
    public = build_public_frame(df)

    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_file = data_dir / "test-00000-of-00001.parquet"
    public.to_parquet(out_file, index=False)

    card_path = output_dir / "README.md"
    card_path.write_text(render_card(public), encoding="utf-8")

    print(f"Wrote {len(public)} rows to {out_file}")
    print(f"  columns ({len(public.columns)}): {list(public.columns)}")
    rv_counts = {k: int(v) for k, v in public["release_version"].value_counts().items()}
    print(f"  communities: {public['community'].nunique()}")
    print(f"  languages:   {public['language'].nunique()}")
    print(f"  release_version: {rv_counts}")
    print(f"  wildcards:   {int(public['is_wildcard'].sum())} / {len(public)}")
    print(f"Wrote dataset card to {card_path}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Export the pilot dataset to a HuggingFace-ready dataset (parquet + card)."
    )
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.input, args.output_dir)
