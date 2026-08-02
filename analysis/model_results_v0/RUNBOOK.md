# Reproducing the v0 results analysis

End-to-end steps to regenerate every table and figure in this folder from
raw run data. Anyone with Drive access can follow this without prior context.
All commands run from `analysis/model_results_v0/` unless noted.

## What this pipeline does

Model run outputs (from the shared Drive) are loaded into one tidy table
(one row per riddle per model), scored by the reference heuristic judge, and
turned into the paper/blog/slides figures plus the HuggingFace export.

## One-time setup

From `analysis/`:

    cd analysis
    uv venv
    uv pip install -r requirements.txt pyarrow jupyter ipykernel

Commands below use `../.venv/bin/python` from `model_results_v0/`.

## Step 1 — Get the run data (not in git)

Download from the shared Drive folder `RiddleBenchmarking`:
- `Responses_v0/` -> `data/responses_v0/` (one folder per model run)

Skip `Cache_v0`. Human eval files go in `data/human_eval_v0/`. `data/` is
gitignored. Do not rename run folders; the loader handles inconsistent
layouts. Exclusions live in `EXCLUDED_FOLDERS` in `load_results.py`.

## Step 2 — Score every run with the heuristic judge

From the repo root:

    cd ..
    for res in analysis/model_results_v0/data/responses_v0/*/*results*.jsonl; do
      analysis/.venv/bin/python evals/reference_heuristic_judge.py "$res"
    done
    cd analysis/model_results_v0

Judge outputs land in `evals/outputs/<run_id>/` (gitignored, regenerable).

## Step 3 — Build the tidy frame

    ../.venv/bin/python load_results.py

Writes `data/processed/results_tidy.parquet` and joins judge scores.
`rows without judge score` should be 0.

## Step 4 — Data quality report

    ../.venv/bin/python data_quality_report.py

Writes `DATA_QUALITY_v0.md`. Per version: pass <parquet> <out.md> <version>.

## Step 5 — Figures

    ../.venv/bin/python figures/leaderboard.py
    ../.venv/bin/python figures/heatmap_topic.py
    ../.venv/bin/python figures/heatmap_community.py
    ../.venv/bin/python figures/heatmap_community_condensed.py
    ../.venv/bin/python figures/community_profile.py
    ../.venv/bin/python figures/failure_modes.py
    ../.venv/bin/python figures/search_delta.py

Each writes PDF + PNG to `figures/out/`. Each is a pure df->fig function
importable from the notebook; styling from `analysis/style.py`.

## Step 6 — HuggingFace export

    ../.venv/bin/python export_model_answers.py

Writes `data/processed/model_answers.parquet` (tier-2 artifact, out of git).
Carries `eval_category` so search-enabled runs stay labelled in the release.
Re-run this whenever the tidy frame (Step 3) changes, e.g. after a rescoring
or a riddle exclusion; otherwise the exported parquet goes stale.

## Step 7 — Notebook

    ../.venv/bin/jupyter nbconvert --to notebook --execute --inplace v0_results_overview.ipynb

Bakes outputs in so it renders on GitHub. Imports from the scripts.

## Adding a model

Drop its run folder into `data/responses_v0/`, rerun steps 2-7. No code
changes if the schema is standard. Search-enabled models are a different
evaluation category: note in captions and flag to leads, not directly
comparable to closed-book runs.

## Key design decisions

- Denominator: accuracy over completed responses; API errors excluded and
  reported as coverage; token-budget truncations count as failed attempts
  (metrics.py).
- Model identity is (model_name, reasoning_mode); two claude-opus-4-7 runs
  differ only by reasoning mode.
- Judge join is on (source_folder, riddle_id), not run_id, because resumed
  runs carry multiple run_ids in one file.
- Topics: instance_topic is community-specific free text; canonical topic
  (8 fixed + wildcard) is derived from riddle_id in heatmap_topic.py.
- Numbers are floors: strict matching, no paraphrase credit, no partial
  score of 2. Human eval and the LLM judge both land higher.

## Still open

- Human eval join + judge-vs-human agreement figure (after eval completes)
- Human-eval leaderboard with cap-bias handling (pending decision)
- human_annotations.parquet tier-3 export
- LLM-judge scoring run (would raise numbers; needs API access)
