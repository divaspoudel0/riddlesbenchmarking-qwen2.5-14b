# RiddlesBenchmarking
MultiCulture Riddles builds naive-written, human-curated cultural riddle benchmarks for solving **culturally specific riddles** across many languages and
communities. 

This repo takes you end-to-end: **build the dataset → run models → score the
results.**

> Source spreadsheets: <https://drive.google.com/drive/folders/1zlcqFiJy7KAZsT6QRX2quy5N32XW09iW>

## Repository layout

| Directory | What it does | Guide |
| --- | --- | --- |
| [`data_loading/`](data_loading/) | Validate contributor submissions and build the pilot dataset(s) | [readme](data_loading/pilot_dataset/README.md) |
| [`framework/`](framework/) | Run models over a dataset and write per-riddle results | [readme](framework/README.md) |
| [`evals/`](evals/) | Score a run's results — deterministic heuristic + LLM-as-a-judge | [readme](evals/README.md) |
| [`analysis/`](analysis/) | Analysis MultiCulture Riddles and Run Results— generates data and figures for publications | [readme](analysis/README.md) |

## The data

Two datasets live in `data_loading/`:

- **Combined pilot (current)** — `data_loading/pilot_dataset/pilot_dataset_v1.jsonl`,
  **6,100 riddles across 61 communities**. Built from three collection rounds (v0,
  v1, and v2); each riddle carries a `run_batch` tag, and
  `pilot_dataset/submission_registry.yaml` lists every community with its language
  and round.
- **Frozen V0 set** — `data_loading/v0_dataset/pilot_dataset_v1.jsonl`,
  **4,400 riddles across 44 communities**. The original round, kept unchanged so
  V0 benchmark runs stay reproducible.

Each line is one riddle (source + English text, reference answers, topic,
community, run batch, optional hint). See the
[dataset README](data_loading/pilot_dataset/README.md) for the full schema.

> To evaluate only the communities added in a later round, pass `--run-batch v1` 
> to both the framework CLI and `riddles_framework.batch.fill`; omit it to run the full set.
> See [`framework/README.md`](framework/README.md).

---

# Running V0 — end to end

Run the model configs over the V0 dataset and score the results — all from the
`framework/` directory.

### 0. Install

```bash
cd framework
uv sync                 # core deps
# uv sync --extra local # only if you also run local (transformers) models
```

### 1. Pick the models

[`framework/configs/benchmark_v0/`](framework/configs/benchmark_v0/) ships
**example** configs — one per model; treat them as templates (edit the model
ids/keys, or drop in your own `<name>.yaml`). The examples:

| Config | Model | API key |
| --- | --- | --- |
| `gpt55_high.yaml` | GPT-5.5 | `OPENAI_API_KEY` |
| `gemini_pro.yaml` | Gemini Pro | `GEMINI_API_KEY` |
| `cohere_tiny_aya.yaml` | Cohere Tiny-Aya | `COHERE_API_KEY` |
| `gemma4_openrouter.yaml` | Gemma 4 (OpenRouter) | `OPENROUTER_API_KEY` |
| `qwen3.5_vllm.yaml` | Qwen 3.5 (vLLM) | `OPENAI_API_KEY` (Placeholder) |

> ⚠️ The shipped configs use **placeholder** model ids. Before a real run, set
> each config's `model_spec.provider_model_name` to a real id and export its API
> key — the [config README](framework/configs/benchmark_v0/README.md) has a
> "Before you run" checklist.

### 2. Set API keys

```bash
export OPENAI_API_KEY=...      # only for the models you intend to run
export GEMINI_API_KEY=...
export COHERE_API_KEY=...
export OPENROUTER_API_KEY=...
```

### 3. Run

**Run directly** — serial (or concurrent if the config sets `batch_mode: true`):

```bash
cd framework
cfg=configs/benchmark_v0/gpt55_high.yaml          # your config
uv run python -m riddles_framework.cli --config $cfg
```

**Or, faster & cheaper** — pre-fill the cache, then run:

```bash
# Step 1 — fill the cache. Pick ONE line, matching your provider:
uv run python -m riddles_framework.batch.fill --config $cfg --workers 12      # Cohere / OpenRouter / Together (concurrent)
uv run python -m riddles_framework.batch.fill --config $cfg --backend batch   # OpenAI / Gemini / Anthropic (offline Batch API, ~50% cheaper)

# Step 2:
uv run python -m riddles_framework.cli --config $cfg
```

Output: `framework/runs/<run_id>/results.jsonl`. See the
[batch guide](framework/src/riddles_framework/batch/README.md) and the
[config reference](framework/configs/benchmark_v0/README.md).

### 4. (Optional) Score the results

> **Not required to complete your task.** The LLM-as-a-judge calls a paid model
> (it spends credits), so feel free to skip scoring — just upload your raw
> `results.jsonl` (step 5). The heuristic evaluator below is free (no LLM).

From the **repo root**, point an evaluator at a run's `results.jsonl`:

```bash
# deterministic reference-answer match (no LLM, no key)
python evals/reference_heuristic_judge.py framework/runs/<run_id>/results.jsonl

# lenient LLM-as-a-judge (credits paraphrases; needs GEMINI_API_KEY)
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
3. **Upload `results.jsonl`** and **`run_config.json`** in a folder — from `framework/runs/<run_id>/`.
4. **Upload the cache too** (encouraged — CacheSaver makes runs reproducible):
   compress the cache folder and upload it:
   ```bash
   tar -czf ID_model-name_cache.tgz -C framework .cache/cachesaver
   ```

---

## More

- **Framework internals & adding a model** — [`framework/README.md`](framework/README.md),
  plus a plain-language walkthrough in
  [`framework/docs/getting-started.md`](framework/docs/getting-started.md).
- **Dataset schema & rebuild** — [`data_loading/`](data_loading/).
- **Publish to HuggingFace** — [`data_loading/RELEASE.md`](data_loading/RELEASE.md).
- **Scoring details** — [`evals/README.md`](evals/README.md).
