# HuggingFace Release Runbook

How to publish a version of the Multicultural Riddles Benchmark to HuggingFace.
Written so anyone with repo and org access can run a release without prior
context. If something here is unclear, fix the doc, not just the problem.

## What gets published

A HuggingFace dataset at `CohereLabsCommunity/multicultural-riddles-benchmark`:
a single parquet (`test` split) plus a dataset card (`README.md`). **Private
first, always.**

## Prerequisites

- Repo write access and a local clone.
- `uv` installed. The export needs `pandas` and `pyarrow` (`uv add pyarrow`).
- A HuggingFace account with **write** access to the `CohereLabsCommunity` org.
  Madeline Smith manages org access.
- A HuggingFace **write token**. Never put it in a file or commit it. Export it
  in your shell for the push only.

## Steps

1. Build the pilot dataset (skip if already current):

   ```
   cd data_loading
   uv run python build_pilot_dataset.py
   ```

   Expect 61 communities, 6100 riddles. These grow with new releases.

2. Export to HuggingFace format:

   ```
   uv run python export_huggingface.py
   ```

   Produces `hf_export/data/test-00000-of-00001.parquet` and `hf_export/README.md`.
   Expect 61 communities, 51 languages, release_version v0:4400 v1:400 v2:1300.

3. Review the card (`hf_export/README.md`), especially the contributor credits.
   They are auto-derived from the inconsistent `author_credit` field and are
   marked provisional. Confirm with contributors before any public release. See
   "Credits to confirm" below.

4. Push privately (creates the repo as private if it does not exist):

   ```
   export HF_TOKEN=...        # your write token, this shell only
   uv run python push_huggingface.py
   ```

5. Verify on HuggingFace: open the repo, confirm it is **private**, the card
   renders, and the data viewer loads.

6. Review: share the private repo with Julia Kreutzer and Károly Boczka.
   Iterate and re-push. Make public only after sign-off.

## What the export keeps and drops

Keeps the 13 public columns: `riddle_id`, `language`, `community`,
`release_version`, `topic`, `is_wildcard`, the riddle and answer text fields,
`riddle_hint`, `riddle_note`, `author_credit`.

Drops internal fields (`instance_result_id`, `created_at`, `source_row_number`,
`raw_template_fields`, `row_status`) and the deprecated `human_*` validation
fields.

## Key decisions and why

- **Human fields are dropped.** The v2 contribution template no longer collects
  human answers or scores, so they are not part of the public dataset. The
  reference answers are the gold.
- **`release_version`** is the internal `run_batch` renamed for the public. It
  marks the collection round a community entered in, so results compare across
  releases. The internal name leaked eval-routing vocabulary; the public name
  is plain provenance.
- **License is CC-BY-4.0 plus an explicit no-training clause.** The project doc
  forbids using the data for training or as synthetic-data seeds; CC-BY-4.0
  alone does not say that, so the card states it separately.
- **Private first, always.** The dataset contains answers and is scrapeable the
  moment it is public. Stay private until the team signs off.

## Data traps the export already handles

- Some reference answers are numbers stored as ints; the export coerces all text
  columns to string.
- JSON nulls become pandas NaN; the export turns them into real nulls, never the
  literal string "nan".

## Who can run this

Operator needs repo write access and HF org access. Natural backups: Chiffon
Nguyen (schema and analysis), Tenney Hu (benchmarking and runs). Madeline Smith
holds HF org access and can grant it.

## Repo

`CohereLabsCommunity/multicultural-riddles-benchmark`, under datasets. Private
until team sign-off.
