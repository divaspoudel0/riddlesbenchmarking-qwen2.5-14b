# Pilot Dataset v1

Generated: 2026-07-31T16:13:35.167580+00:00
Total submissions: 61
Total riddles: 6100
Run batches: v0, v1, v2

> **Naming note.** The `v1` in the filename `pilot_dataset_v1.jsonl` is the
> dataset *schema* version; it becomes v2 when `raw_template_fields` is
> dropped. The `v1` in the `run_batch` field is a *collection round*, the
> second wave of communities. These are separate axes. To evaluate only the
> newly added communities, select by `run_batch` (the eval CLI's
> `--run-batch` flag), not by the filename. See Versioning below.

## Purpose

First consolidated dataset for the framework team (T2.2.1).
Includes only submissions that passed all validator blocking checks.
Schema follows the Analysis team's canonical instance schema.
Combines all run batches into one dataset; each riddle is tagged with
its `run_batch` so evaluation runs can target only new or changed
communities. See Versioning below.

## Schema

Each line is one riddle as a JSON object. Fields:

| Field | Type | Description |
|---|---|---|
| `instance_result_id` | string (UUID v4) | Unique per row |
| `riddle_id` | string | Stable structured ID: `{community}_{topic}_{number}` |
| `created_at` | ISO 8601 | When this dataset was built |
| `source_row_number` | int | Original row number in contributor's spreadsheet |
| `language` | string (ISO 639-2/3) | Language code, per project metadata spec |
| `community` | string | Community token (e.g. `tamil_india`) |
| `run_batch` | string | Submission batch this community entered or was last changed in (`v0`, `v1`, ...). Internal; dropped from the HuggingFace release. |
| `topic` | string | Topic name as submitted |
| `is_wildcard` | bool | True if topic is community-specific, not one of the 8 standard topics |
| `riddle_original` | string | Riddle text in source language |
| `riddle_english` | string | English translation |
| `reference_answer_original` | string | Reference answer in source language |
| `reference_answer_english` | string | Reference answer in English |
| `riddle_hint` | string or null | Optional hint |
| `riddle_note` | string or null | Optional comment about region/generation specificity |
| `author_credit` | string or null | Submitter name |
| `human_validator_name` | string or null | Person who scored the human answer |
| `human_answer_original` | string or null | Human evaluator's answer attempt |
| `human_answer_score` | string or null | 0-2 rating (raw label from spreadsheet) |
| `human_answer_comment` | string or null | Comment on the human answer |
| `row_status` | string | `"valid"` for all rows in v1 |
| `raw_template_fields` | object | Original column names → values, for any field not in canonical schema. Dropped in v2. |

## Coverage

| Community | Batch | Riddles |
|---|---|---|
| `afaan_oromo_oromo` | v2 | 100 |
| `arabic_egypt` | v0 | 100 |
| `arabic_lebanese` | v2 | 100 |
| `arabic_morocco` | v0 | 100 |
| `arabic_sudan` | v0 | 100 |
| `arabic_syria` | v0 | 100 |
| `assamese_india` | v1 | 100 |
| `belarusian_belarus` | v0 | 100 |
| `bengali_bangladesh` | v0 | 100 |
| `bengali_india` | v0 | 100 |
| `brazilian_portuguese` | v0 | 100 |
| `bugisnese_indonesia` | v0 | 100 |
| `bulgarian_bulgaria` | v0 | 100 |
| `cantonese_china` | v0 | 100 |
| `catalan_catalonia` | v2 | 100 |
| `chinese_china` | v0 | 100 |
| `chinese_malaysia` | v2 | 100 |
| `chinese_simplified_china` | v0 | 100 |
| `chinese_singapore` | v2 | 100 |
| `dutch_netherlands` | v0 | 100 |
| `english_canada` | v0 | 100 |
| `english_usa` | v0 | 100 |
| `french_canada` | v2 | 100 |
| `french_france` | v0 | 100 |
| `german_germany` | v0 | 100 |
| `gujarati_india` | v2 | 100 |
| `hungarian_hungary` | v0 | 100 |
| `indonesian_indonesia` | v0 | 100 |
| `italian_italy` | v0 | 100 |
| `japanese_japan` | v2 | 100 |
| `kannada_india` | v1 | 100 |
| `konkani_india` | v0 | 100 |
| `luganda_uganda` | v0 | 100 |
| `lumasaba_uganda` | v0 | 100 |
| `luxembourgish_luxembourg` | v2 | 100 |
| `malay_malaysia` | v2 | 100 |
| `malayalam_india` | v0 | 100 |
| `marathi_india` | v0 | 100 |
| `mongondow_indonesia` | v0 | 100 |
| `nepali_nepal` | v0 | 100 |
| `persian_iran` | v0 | 100 |
| `polish_poland` | v0 | 100 |
| `portuguese_portugal` | v0 | 100 |
| `russian_russia` | v0 | 100 |
| `serbian_serbia` | v0 | 100 |
| `sindhi_india` | v2 | 100 |
| `sinhala_sri_lanka` | v0 | 100 |
| `spanish_argentina` | v0 | 100 |
| `spanish_cuba` | v0 | 100 |
| `spanish_peru` | v0 | 100 |
| `swahili_kenya` | v0 | 100 |
| `tamil_india` | v0 | 100 |
| `telugu_india` | v0 | 100 |
| `thai_thailand` | v0 | 100 |
| `tunisian_arabic_tunisia` | v1 | 100 |
| `turkish_turkey` | v2 | 100 |
| `ukrainian_ukraine` | v1 | 100 |
| `urdu_pakistan` | v0 | 100 |
| `uzbek_uzbekistan` | v0 | 100 |
| `vietnamese_vietnam` | v2 | 100 |
| `yoruba_nigeria` | v0 | 100 |

## Design decisions

- **Anti-corruption layer**: contributors write to the template schema;
  this script transforms once at the boundary to canonical schema. Single
  point of truth, no per-team conversion drift.
- **ISO 639-2/3 language codes**: matches Analysis team's instance schema.
  Arabic dialects use 639-3 codes (`arz`, `apd`, `apc`, `ary`); macro-language
  `ara` would lose dialect information critical to a cultural benchmark.
- **Verified language codes by source inspection**: Egyptian, Sudanese,
  Syrian, Moroccan, Cantonese, Mongondow language codes were confirmed by
  reading actual riddle content rather than guessing from filenames.
  (Sudanese was initially mismapped to Sundanese before verification.)
- **Script-family sanity check**: build runs a Unicode block check against
  the expected script family. Warnings printed but don't block the build.
- **`raw_template_fields` nested object**: preserves any column not in
  the canonical mapping (e.g. custom transliteration columns some
  contributors added). Allows v1 consumers to recover original data if
  needed. Dropped in v2 once mappings are validated.
- **Structured `riddle_id`**: stable across rebuilds, human-readable,
  sortable by community → topic → number.

## Open questions

1. **English + hints condition**: hints are written in source language
   only. Should hints be translated for the English condition, or
   fed mixed-language?
2. **`human_answer_score` field**: kept as raw string label (e.g.
   `"2: correct"`) for v1 because contributor files use inconsistent
   formats. Should be parsed to int 0/1/2 in v2.
3. **Scoring scale mismatch**: contributor template uses a 0-2 scale
   for `Rating of Human Answer`, while the project metadata schema
   and aggregate metrics use a 0-3 scale (0=hallucination, 1=honest
   uncertainty, 2=partial, 3=correct). Needs reconciliation before
   benchmarking starts.

## How to rebuild

```bash
cd data_loading
# validate each batch into its own reports directory
uv run python validate_submissions.py --run-batch v0 --no-download
uv run python validate_submissions.py --run-batch v1 --no-download
# combine all batches into the dataset + registry
uv run python build_pilot_dataset.py
# or build a single batch:
uv run python build_pilot_dataset.py --batches v1
```

## Versioning

Two independent version axes. Do not conflate them.

### Run batches

Communities are grouped into run batches: `v0` is the original
collection, `v1` the next round, and so on. Every riddle carries a
`run_batch` tag, and the build also writes `submission_registry.yaml`,
a per-community manifest of language, run_batch, and riddle count.

The registry is the human-readable manifest of which community is in
which batch. Model runs are self-funded, so teams should not re-pay to
evaluate communities they already ran. Each riddle carries its
`run_batch`, and the eval CLI filters on it: pass `--run-batch v1` to
cover only the new and corrected communities, or omit the flag to run
all batches when bringing a new model online. A community that is
corrected and re-submitted in a later batch is bumped to that batch, so
a `--run-batch v1` run correctly re-runs it.

### Schema versions

- **v1** (this version): includes `raw_template_fields` for forward
  compatibility. Analysis team consumes canonical fields; data preserved
  for review.
- **v2** (planned): drops `raw_template_fields` after Analysis confirms
  the mapping is complete. May parse `human_answer_score` to int and
  reconcile the 0-2 vs 0-3 scoring scale mismatch.