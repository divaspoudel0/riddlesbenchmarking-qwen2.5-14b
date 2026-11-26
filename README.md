# RiddlesBenchmarking

**MultiCulture Riddles** builds naive-written, human-curated benchmarks for
solving **culturally specific riddles** across many languages and communities.

The repo takes you end to end — **build the dataset → run models → score the
results → analyze** — with a reproducible pipeline, committed example runs, and
publication-ready figures.

> Source spreadsheets: [Google Drive folder](https://drive.google.com/drive/folders/1zlcqFiJy7KAZsT6QRX2quy5N32XW09iW)

## Contents

- [Repository structure](#repository-structure)
- [The pipeline](#the-pipeline)
- [Datasets](#datasets)
- [Quickstart: run and score V0 end to end](#quickstart-run-and-score-v0-end-to-end)
- [Results and reproducibility](#results-and-reproducibility)
- [Contributing](#contributing)
- [Documentation index](#documentation-index)

## Repository structure

```
.
├── data_loading/           # build & validate the dataset(s)
├── framework/              # run models over the dataset
│   ├── configs/            #   run configs (one YAML per model)
│   ├── docs/               #   getting-started + code reference
│   ├── molab/              #   marimo notebook: Qwen2.5 AWQ on molab
│   ├── runs/               #   run artifacts (results.jsonl, manifest)
│   ├── src/                #   the riddles_framework package
│   └── tests/
├── evals/                  # score a run (heuristic + LLM judge)
├── analysis/               # figures, tables, data-quality reports
│   ├── model_results_v0/   #   model-performance analysis
│   ├── v1_analysis/        #   dataset-side analysis (v1 round)
│   ├── riddle_survey_analysis/
│   └── humaneval_validation/
├── benchmark_results/      # packaged runs + caches
├── README.md
└── RIDDLE_CORRECTIONS.md   # process for fixing a riddle after a run
```

### Directory guide

| Directory | What it does | Guide |
| --- | --- | --- |
| [`data_loading/`](data_loading/) | Validate contributor submissions, build the pilot/V0/5-language datasets, export to HuggingFace | [README](data_loading/README.md) |
| [`framework/`](framework/) | Run models over a dataset and write per-riddle results | [README](framework/README.md) |
| [`framework/molab/`](framework/molab/) | Hosted marimo notebook that runs Qwen2.5 AWQ on molab | [README](framework/molab/README.md) |
| [`framework/runs/`](framework/runs/) | Committed run artifacts and their contract | [README](framework/runs/README.md) |
| [`evals/`](evals/) | Score results — deterministic heuristic + LLM-as-a-judge | [README](evals/README.md) |
| [`analysis/`](analysis/) | Analysis of the data and run results; generates publication figures | [README](analysis/README.md) |
| [`benchmark_results/`](benchmark_results/) | Packaged runs and CacheSaver caches for reproducibility | [README](benchmark_results/README.md) |
| [`RIDDLE_CORRECTIONS.md`](RIDDLE_CORRECTIONS.md) | How to fix a riddle after a version has already run | — |

## The pipeline

```
                 ┌────────────────┐
  submissions ──►│ data_loading/  │──► pilot_dataset_v1.jsonl
                 └────────────────┘
                          │
                          ▼
                 ┌────────────────┐
                 │  framework/    │──► framework/runs/<run_id>/results.jsonl
                 └────────────────┘
                          │
                          ▼
                 ┌────────────────┐
                 │    evals/      │──► heuristic_match.jsonl / llm_judge.jsonl
                 └────────────────┘
                          │
                          ▼
                 ┌────────────────┐
                 │  analysis/     │──► figures/ + csv/ + data-quality reports
                 └────────────────┘
```

- **`benchmark_results/`** archives packaged runs + caches for submission.
- **`framework/molab/`** is a self-contained hosted runner for the Qwen2.5 AWQ
  models and writes into `framework/runs/` and `benchmark_results/`.

## Datasets

All datasets live in `data_loading/` as JSONL — one riddle per line.

| Dataset | File | Size | Use |
| --- | --- | --- | --- |
| **Combined pilot** (current) | [`pilot_dataset/pilot_dataset_v1.jsonl`](data_loading/pilot_dataset/pilot_dataset_v1.jsonl) | 6,100 riddles · 61 communities | Full benchmark. Built from rounds `v0`, `v1`, `v2`; filter with `--run-batch`. |
| **Frozen V0 set** | [`v0_dataset/pilot_dataset_v1.jsonl`](data_loading/v0_dataset/pilot_dataset_v1.jsonl) | 4,400 riddles · 44 communities | Original round, kept unchanged so V0 runs stay reproducible. |
| **5-language subset** | [`pilot_dataset/pilot_dataset_5lang.jsonl`](data_loading/pilot_dataset/pilot_dataset_5lang.jsonl) | 500 riddles · 5 communities | Hungarian, Tamil, Moroccan Arabic, Russian, Chinese. |
| **Smoke test** | [`pilot_dataset/smoke_test_25.jsonl`](data_loading/pilot_dataset/smoke_test_25.jsonl) | 25 riddles | Quick config sanity check. |

Each line carries the source + English riddle text, reference answers, topic,
community, `run_batch`, and an optional hint. See the
[dataset README](data_loading/pilot_dataset/README.md) for the full schema and
the [5-language README](data_loading/pilot_dataset/pilot_dataset_5lang_README.md)
for that subset.

> **Two version axes.** The `v1` in `pilot_dataset_v1.jsonl` is the *schema*
> version; the `v1` in `run_batch` is a *collection round*. To evaluate only the
> communities added later, pass `--run-batch v1` to both the framework CLI and
> `riddles_framework.batch.fill`; omit it to run the full set.

## Quickstart: run and score V0 end to end

Run the model configs over the V0 dataset and score the results. Commands run
from the `framework/` directory unless noted.

### 0. Install

```bash
cd framework
uv sync                  # core deps (API providers)
# uv sync --extra local  # also install torch/transformers for local models
```

Requires Python 3.10+ and [`uv`](https://docs.astral.sh/uv/).

### 1. Pick the models

[`framework/configs/benchmark_v0/`](framework/configs/benchmark_v0/) ships
**example** configs — one per model. Treat them as templates (edit the model
ids/keys, or drop in your own `<name>.yaml`).

| Config | Model | Provider | API key |
| --- | --- | --- | --- |
| `gpt55_high.yaml` | GPT-5.5 | openai | `OPENAI_API_KEY` |
| `gemini_pro.yaml` | Gemini Pro | google | `GEMINI_API_KEY` |
| `cohere_tiny_aya.yaml` | Cohere Tiny-Aya | cohere | `COHERE_API_KEY` |
| `cohere_command_plus.yaml` | Cohere Command A+ | cohere | `COHERE_API_KEY` |
| `gemma4_openrouter.yaml` | Gemma 4 | openrouter | `OPENROUTER_API_KEY` |
| `qwen2.5_14b_awq.yaml` | Qwen2.5-14B-Instruct-AWQ | local (GPU) | — |
| `qwen2.5_32b_awq.yaml` | Qwen2.5-32B-Instruct-AWQ | local (GPU) | — |
| `qwen3.5_vllm.yaml` | Qwen 3.5 (vLLM) | vllm | `OPENAI_API_KEY` (placeholder) |

> **Before a real run:** the shipped configs use **placeholder** model ids. Set
> each config's `model_spec.provider_model_name` to a real id and export its key.
> The [config README](framework/configs/benchmark_v0/README.md) has a full
> "Before you run" checklist. Local AWQ runs also need the model weights
> downloaded from Hugging Face and a suitable GPU.

### 2. Set API keys

```bash
export OPENAI_API_KEY=...      # only for the models you intend to run
export GEMINI_API_KEY=...
export COHERE_API_KEY=...
export OPENROUTER_API_KEY=...
```

### 3. Run

**Run directly** — serial, or concurrent when the config sets `batch_mode: true`:

```bash
cfg=configs/benchmark_v0/gpt55_high.yaml          # your config
uv run python -m riddles_framework.cli --config $cfg
```

**Or, faster & cheaper** — pre-fill the cache, then run:

```bash
# Step 1 — fill the cache. Pick ONE line, matching your provider:
uv run python -m riddles_framework.batch.fill --config $cfg --workers 12      # Cohere / OpenRouter / Together (concurrent)
uv run python -m riddles_framework.batch.fill --config $cfg --backend batch   # OpenAI / Gemini / Anthropic (offline Batch API, ~50% cheaper)

# Step 2 — run (instant cache hits):
uv run python -m riddles_framework.cli --config $cfg
```

Output: `framework/runs/<run_id>/results.jsonl`. See the
[batch guide](framework/src/riddles_framework/batch/README.md) and the
[config reference](framework/configs/benchmark_v0/README.md).

### 4. (Optional) Score the results

> **Not required to complete your task.** The LLM-as-a-judge calls a paid model
> (it spends credits), so you can skip scoring and upload your raw
> `results.jsonl` (step 5). The heuristic evaluator below is free (no LLM).

From the **repo root**, point an evaluator at a run's `results.jsonl`:

```bash
# Deterministic reference-answer match (no LLM, no key)
python evals/reference_heuristic_judge.py framework/runs/<run_id>/results.jsonl

# Lenient LLM-as-a-judge (credits paraphrases; needs GEMINI_API_KEY)
python -m evals.llm_judge_run framework/runs/<run_id>/results.jsonl
```

The heuristic evaluator writes a per-riddle score file and a summary; the LLM
judge writes verdicts next to the run. See the [evals README](evals/README.md).

### 5. Submit your results

Final outputs are collected in a shared
**[Google Drive folder](https://drive.google.com/drive/folders/1ow1GKXeaOFJJr_59-Qg7erQf046mi2t1?usp=drive_link)**.
Find your assigned task ID in the
**[tracking sheet](https://docs.google.com/spreadsheets/d/1jK8ESbHB3EaMg4kOinEAfpseGh64SypWsRM28mLctFA/edit?gid=0#gid=0)**.

1. **Update the tracking sheet** — set your status when you **start** and when
   you **complete** your assigned task.
2. **Name your files `ID_model-name`** — `ID` must match the one listed for you
   in the sheet (e.g. `07_gpt-5.5`).
3. **Upload `results.jsonl`** and **`run_config.json`** in a folder — from
   `framework/runs/<run_id>/`.
4. **Upload the cache too** (encouraged — CacheSaver makes runs reproducible):
   compress the cache folder and upload it:
   ```bash
   tar -czf ID_model-name_cache.tgz -C framework .cache/cachesaver
   ```

## Results and reproducibility

- **Committed runs** — [`framework/runs/`](framework/runs/) holds the Qwen2.5-14B
  AWQ runs (v0/v1/v2), four 5-language pilot runs, and a 25-riddle example run.
  See the [runs README](framework/runs/README.md) for the table.
- **Caches** — [`benchmark_results/`](benchmark_results/) stores packaged
  CacheSaver tarballs so answers can be reproduced without re-calling providers.
- **Figures** — [`analysis/`](analysis/) regenerates every publication figure
  from run data; the [V0 runbook](analysis/model_results_v0/RUNBOOK.md) walks
  through it step by step.
- **Local weights** — AWQ configs require the model weights (downloaded from
  Hugging Face) and a GPU; they are not stored in this repo.

## Contributing

- **Adding a model** — don't touch the runner; follow
  [`framework/CONTRIBUTING.md`](framework/CONTRIBUTING.md).
- **Submitting riddles** — validate workbooks with `data_loading/` first; see
  [`data_loading/README.md`](data_loading/README.md).
- **Fixing a riddle after a run** — follow
  [`RIDDLE_CORRECTIONS.md`](RIDDLE_CORRECTIONS.md) (freeze principle: fix the
  source, exclude from the frozen version's analysis, re-evaluate next round).
- **Branch naming** — `fix/riddle-<community>-<id>` for one-off fixes,
  `chore/…` for process/tooling changes.

## Documentation index

| Topic | Where |
| --- | --- |
| Dataset schema, rebuild, communities | [`data_loading/pilot_dataset/README.md`](data_loading/pilot_dataset/README.md) |
| Publish to HuggingFace | [`data_loading/RELEASE.md`](data_loading/RELEASE.md) |
| Framework internals & adding a model | [`framework/README.md`](framework/README.md) · [`CONTRIBUTING.md`](framework/CONTRIBUTING.md) |
| Plain-language walkthrough | [`framework/docs/getting-started.md`](framework/docs/getting-started.md) |
| File-by-file code reference | [`framework/docs/code-reference.md`](framework/docs/code-reference.md) |
| Batch / cache guide | [`framework/src/riddles_framework/batch/README.md`](framework/src/riddles_framework/batch/README.md) |
| Scoring details | [`evals/README.md`](evals/README.md) |
| Analysis overview | [`analysis/README.md`](analysis/README.md) |
| V0 model-results runbook | [`analysis/model_results_v0/RUNBOOK.md`](analysis/model_results_v0/RUNBOOK.md) |
