# Benchmark — V0 dataset

Runs four models over
[`v0_dataset/pilot_dataset_v1.jsonl`](../../../data_loading/v0_dataset/pilot_dataset_v1.jsonl)
— the **V0 dataset: 4,400 riddles across 44 communities**.

| Config | Model | Provider / access | API key |
| --- | --- | --- | --- |
| `gpt55_high.yaml` | GPT-5.5 | openai / direct_api | `OPENAI_API_KEY` |
| `gemini_pro.yaml` | Gemini Pro | google / direct_api | `GEMINI_API_KEY` |
| `cohere_tiny_aya.yaml` | Cohere Tiny-Aya (`tiny-aya-global`) | cohere / direct_api | `COHERE_API_KEY` |
| `gemma4_openrouter.yaml` | Gemma 4 (open weights) | openrouter / openrouter | `OPENROUTER_API_KEY` |
| `qwen3.5_vllm.yaml` | Qwen 3.5 (vLLM) | vllm / direct_api |`OPENAI_API_KEY` (Placeholder) |


These are **example configs** — treat them as templates: edit the model
ids/keys, change the condition, or add your own config for any model. All five
share the same run condition for comparability: prompt `riddle_master` v1,
English prompt, source-language riddle, no hint, `max_output_tokens: 4096`. JSON
output is prompt-driven (the `riddle_master` prompt asks for a JSON object), so
there is no `response_format` knob.

## ⚠️ Before you run — what to change

The run script will run **whatever configs are in this folder**, but the shipped
ones are templates with **placeholder model ids**. For each model you want to
run, edit its `*.yaml`:

1. **`model_spec.provider_model_name`** → a real model id your account can call.
   Current placeholders (confirm/replace each):

   | Config | `provider_model_name` (placeholder) | `api_key_env_var` |
   | --- | --- | --- |
   | `gpt55_high.yaml` | `gpt-5.5` | `OPENAI_API_KEY` |
   | `gemini_pro.yaml` | `gemini-3.1-pro-preview` | `GEMINI_API_KEY` |
   | `cohere_tiny_aya.yaml` | `tiny-aya-global` | `COHERE_API_KEY` |
   | `gemma4_openrouter.yaml` | `google/gemma-4-31b-it` | `OPENROUTER_API_KEY` |
   | `qwen3.5_vllm.yaml` | `Qwen/Qwen3.5-0.8B` | `OPENAI_API_KEY` (Placeholder) |


2. **Export the API key** named by that config's `api_key_env_var` (above).

That's the minimum. Optional: tune any field — see the
[full reference](#configuration-reference) below.

## Run

**Run directly** — serial (or concurrent if the config sets `batch_mode: true`):

```bash
cd framework
cfg=configs/benchmark_v0/gpt55_high.yaml          # your config
uv run python -m riddles_framework.cli --config $cfg
```

**Or, faster & cheaper** (recommended for a real 4,400-riddle pass) — pre-fill
the cache, then run:

```bash
# Step 1 — fill the cache. Pick ONE line, matching your provider:
uv run python -m riddles_framework.batch.fill --config $cfg --workers 12      # Cohere / OpenRouter / Together (concurrent)
uv run python -m riddles_framework.batch.fill --config $cfg --backend batch   # OpenAI / Gemini / Anthropic (offline Batch API, ~50% cheaper)

# Step 2 — run (always; instant, reads from cache):
uv run python -m riddles_framework.cli --config $cfg
```

See the [batch guide](../../src/riddles_framework/batch/README.md). Output:
`framework/runs/<run_id>/results.jsonl`; score with
[`../../../evals`](../../../evals/README.md).

---

## Configuration reference

Each `*.yaml` here is one run config. Below is every field you may need to set.

### ⚠️ Must set before a real (billed) run

| Field | What to set |
| --- | --- |
| `model_spec.provider_model_name` | The **exact** model id your account can call (e.g. `gpt-5.5`, `gemini-3.1-pro-preview`, `tiny-aya-global`, `google/gemma-4-31b-it`). The shipped values are placeholders. |
| `api_key_env_var` + the env var | The env var name the adapter reads the key from, and the key exported in your shell (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `COHERE_API_KEY`, `OPENROUTER_API_KEY`). |
| `base_url` | `null` for direct APIs; set for routed providers (OpenRouter: `https://openrouter.ai/api/v1`). |

### Dataset

| Field | Meaning |
| --- | --- |
| `dataset_path` | Path to the JSONL, relative to `framework/` — `../data_loading/v0_dataset/pilot_dataset_v1.jsonl` for V0. |
| `dataset_version` | Label recorded in the output (`pilot_dataset_v1`). |

### Prompt & condition

| Field | Meaning | V0 value |
| --- | --- | --- |
| `prompt_template_id` / `prompt_template_version` | Which instruction template (only `riddle_master` / `v1` ships). | `riddle_master` / `v1` |
| `prompt_language` | Language of the instructions. | `eng` |
| `riddle_language_presented` | `source` (native language) or `english`. | `source` |
| `is_hint_provided` | Include the riddle's hint in the prompt. | `false` |

### Generation

| Field | Meaning | Notes |
| --- | --- | --- |
| `reasoning_mode` | `null`, or e.g. `high` for reasoning models (`reasoning_effort` / extended thinking). | requires `capabilities.supports_reasoning` |
| `search_enabled` | Enable web search. | requires `supports_search` |
| `max_output_tokens` | Output token cap. | `4096` |
| `temperature` | `null` = provider default. | — |
| `seed` | `null`, or an int for reproducibility. | requires `supports_seed` |
| `model_params` | Extra kwargs passed straight to the provider SDK (e.g. `{top_p: 0.95}`). | — |

### Caching

| Field | Meaning |
| --- | --- |
| `cache_enabled` | Reuse cached answers for identical requests. |
| `cache_backend` | `cachesaver` (the only backend). |
| `cache_namespace` | Logical partition (`multicultural_riddles/<dataset>/<model>/<condition>/<prompt>`). |
| `cache_dir` | On-disk cache location (`.cache/cachesaver`). |

### Concurrency (in-run)

| Field | Meaning |
| --- | --- |
| `batch_mode` | `true` runs `batch_size` requests concurrently per batch (OpenAI-compatible adapters: Cohere, OpenRouter). |
| `batch_size` | Concurrency when `batch_mode: true`. |
| `model_spec.capabilities.supports_batch` | Must be `true` for `batch_mode`. |

`gpt55_high` / `gemini_pro` keep `batch_mode: false` (use the offline Batch API
for those — see the batch guide); `cohere_tiny_aya` / `gemma4_openrouter` ship
with `batch_mode: true`, `batch_size: 12`.

### `model_spec`

| Field | Meaning |
| --- | --- |
| `model_name` / `model_id` | Human label / internal id (provider-prefixed). |
| `provider` | `openai` / `google` / `cohere` / `openrouter` — selects the adapter. |
| `access_pattern` | `direct_api` or `openrouter`. |
| `provider_model_name` | **The string sent to the API** (see "must set" above). |
| `closed_source` | Metadata flag. |
| `capabilities.*` | `supports_reasoning` / `_search` / `_structured_output` / `_batch` / `_seed` — the runner refuses a run that requests a capability set to `false`. |

### Misc

| Field | Meaning |
| --- | --- |
| `runner_name` | Free label for who/what ran it (`benchmark_v0`). |
| `runner_version` | Version stamp recorded in output. |
| `notes` | Free text. |
| `strict_capability_check` | Keep `true` to validate the run against `capabilities`. |
