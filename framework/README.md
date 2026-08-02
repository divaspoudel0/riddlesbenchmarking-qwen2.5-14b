# Benchmark Framework (T2.2.1)

Base benchmarking framework for the Multicultural Riddles project.

## Layout

```
framework/
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
├── configs/                              # example run configs (YAML)
├── docs/                                 # human-readable docs
│   ├── getting-started.md                # plain-language guide
│   └── code-reference.md                 # file-by-file technical reference
├── tests/                                # pytest suite
└── src/
    └── riddles_framework/                # the installed package
        ├── constants.py
        ├── exceptions.py
        ├── schemas.py
        ├── utils.py
        ├── community_display.py              # community key → display name mapping
        ├── dataset_loader.py
        ├── prompts.py
        ├── prompt_templates/                 # instruction templates (YAML)
        │   └── riddle_master_v1.yaml
        ├── writers.py
        ├── registry.py
        ├── factory.py
        ├── cache_clients.py
        ├── runner.py
        ├── yaml_config.py
        ├── model_specs.py
        ├── cli.py
        ├── batch/                            # faster & cheaper results (concurrent + Batch APIs)
        │   └── README.md
        └── models/                           # provider adapters
            ├── base.py                       # Model ABC every adapter implements
            ├── concurrent_batch.py           # concurrent generate_batch (batch_mode)
            ├── dummy.py                      # reference adapter, used for smoke tests
            ├── openai_adapter.py
            ├── anthropic_adapter.py
            ├── gemini_adapter.py
            ├── cohere_adapter.py
            ├── openrouter_adapter.py
            ├── together_adapter.py
            └── transformers_local_adapter.py
```

## What this framework does

- loads the pilot dataset JSONL
- builds prompts for benchmark conditions
- runs models through a stable model interface
- supports multiple providers and access patterns
- optionally uses CacheSaver for caching and reproducibility
- writes standardized run artifacts for downstream evaluation

## What it does not do

- build the dataset (that's the data-loading package)
- define automatic scoring (T2.3)
- perform human evaluation

## Input

```
../data_loading/pilot_dataset/pilot_dataset_v1.jsonl
```

The pilot dataset is produced by the sibling `data_loading/` package via `build_pilot_dataset.py`. The framework reads it as a finished artifact — it doesn't validate or modify the file. If you need a new build, run that script in `data_loading/` first.

## Output

```
runs/<run_id>/
  run_config.json
  run_metadata.json
  results.jsonl
  manifest.json
```

This is the contract for the analysis team.

## Benchmark conditions

Supported: `source_no_hint`, `source_with_hint`, `english_no_hint`.

Not supported in v1: `english_with_hint`. The runner fails fast before touching the filesystem if this is configured.

## Design choices (per project lead feedback)

These are non-obvious and worth knowing before changing anything:

**Temperature is `Optional[float]` and defaults to `None`.** Many reasoning models (OpenAI o-series, Anthropic thinking, DeepSeek R1) can fall into degenerate loops at low temperature. We let the model's default apply unless temperature is explicitly set in the YAML. Setting `temperature: null` or omitting it altogether is the recommended path for reasoning runs.

**Arbitrary provider parameters via `model_params:`.** Rather than adding a new `RunConfig` field every time someone wants `top_p` or `frequency_penalty`, the YAML config takes a `model_params:` dict that flows verbatim into the provider's request, merged LAST so it overrides anything the adapter set automatically. Use it for top_p, frequency_penalty, presence_penalty, top_k, etc.

**Default response format is JSON.** Per project guidance, structured output is the default. Set `response_format: free_form` in YAML if you need free text.

**Prompt templates live as YAML files, selectable by `(template_id, template_version)`.** See `src/riddles_framework/prompt_templates/`. To add a new template, drop in a new YAML file with `template_id`, `template_version`, and `instruction_text`. No code change required. Optional `recommended_response_format` is informational; the actual format used is whatever `RunConfig.response_format` says.

## Install

This project uses [`uv`](https://docs.astral.sh/uv/) to manage the environment and dependencies. If you don't have it yet:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

API-only (no torch). Works for OpenAI, Anthropic, Gemini, and OpenRouter (which uses the OpenAI SDK under the hood):

```bash
uv sync
```

With local inference (also installs torch + transformers; needed for the local Hugging Face adapter):

```bash
uv sync --extra local
```

Local Hugging Face runs use `configs/local_transformers_example.yaml` as a scaffold. Set
`model_spec.provider_model_name` to the Hugging Face model id you want to run, keep
`response_format: free_form` unless the model is known to return valid JSON, and enable
`cache_enabled` to route generation through CacheSaver's local Transformers wrapper.
Set `batch_mode: true` and choose `batch_size` to run local generation through
the adapter-level `generate_batch` path; keep `batch_mode: false` for serial runs.
Use `local_cache_client_mode: sync`: the pinned CacheSaver (`==0.0.6`) only ships
a sync local Transformers wrapper, so `async` is not available and will raise.
For GPU loading, set `model_params.model_load.device_map: auto`; the `local`
extra installs `accelerate` so Transformers can place weights on GPU.
For a quick, GPU-independent check that the local adapter works end to end, run
`configs/local_cpu_smoke.yaml` (a small ungated model pinned to CPU); every
`results.jsonl` row should report `generation_status: success`.
If `uv run python scripts/check_local_gpu.py` reports `torch.version.cuda: None`,
the active environment still has CPU-only Torch. Reinstall the CUDA wheel with:

```bash
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130 --reinstall-package torch
```

## Run

Smoke test with the dummy model (no API calls):

```bash
uv run python -m riddles_framework.cli --config configs/dummy.yaml
```

Smoke test with cultural-context substitution (also dummy, no API calls; verifies the placeholder system end-to-end):

```bash
uv run python -m riddles_framework.cli --config configs/dummy_cultural_context.yaml
```

Real provider:

```bash
export OPENAI_API_KEY=...
uv run python -m riddles_framework.cli --config configs/openai_gpt55_high.yaml
```

For non-engineer contributors, see `docs/getting-started.md` for a plain-language walkthrough and `docs/code-reference.md` for the file-by-file technical reference.

### Running a single batch

The pilot dataset is tagged by submission batch (`run_batch`: `v0`, `v1`, ...).
To evaluate only the communities from one batch, pass `--run-batch`:

```bash
# only the v1 communities (e.g. a model already run on v0)
uv run python -m riddles_framework.cli --config <cfg> --run-batch v1

# the full set (e.g. a new model) — omit the flag
uv run python -m riddles_framework.cli --config <cfg>
```

This complements the cache rather than replacing it. A warm cache already
avoids re-paying for prompts a model has seen; `--run-batch` additionally
skips processing the other batches entirely, which is faster and writes a
`results.jsonl` scoped to just those communities. It can also be set in the
config as `run_batches: [v1]`; the CLI flag overrides it. The selected batches
are recorded in each run's `run_metadata.json` and `manifest.json`.

### Getting results faster and cheaper

The runner sends requests serially. Three faster paths (all share one cache, so
results are interchangeable with a normal `cache_enabled` run):

```bash
# 1. Concurrency inside a normal run — set in the config (Cohere / OpenRouter):
#      batch_mode: true   batch_size: 12   (capabilities.supports_batch: true)
uv run python -m riddles_framework.cli --config <cfg>

# 2. Pre-fill the cache concurrently, then run (OpenAI-compatible providers):
uv run python -m riddles_framework.batch.fill --config <cfg> --workers 12
uv run python -m riddles_framework.cli --config <cfg>          # instant cache hits

# 3. Offline Batch API, ~50% cheaper (OpenAI / Anthropic / Gemini):
uv run python -m riddles_framework.batch.fill --config <cfg> --backend batch
uv run python -m riddles_framework.cli --config <cfg>
```

See [`src/riddles_framework/batch/README.md`](src/riddles_framework/batch/README.md)
for the full guide: provider support, flags, cache formats, and test status.

## Tests

```bash
uv run pytest
```

## Known v1 limitations

- **Refusal tagging is heuristic, conservative, and English-only.** Tags clear policy refusals (e.g. "I can't help with that") but does NOT tag honest uncertainty (e.g. "I cannot determine") as a refusal — that's a signal the benchmark wants to measure, not suppress. Source-language refusals will not be tagged. Downstream T2.3 / human eval may refine this.
- **`model_specs.py` and the configs' `provider_model_name` fields are scaffolds.** Placeholder strings (`gpt-5.5-high`, `claude-opus-4.7`, etc.) must be replaced with real provider strings your team has access to before any production run.
- **Resume mode is not implemented.** If a run crashes mid-way, the entire run must be re-executed. Cache (when enabled) will short-circuit already-seen prompts, but `results.jsonl` itself starts fresh per run.
- **Provider SDK surfaces evolve.** Some adapter-level knobs (reasoning effort, web search toggles, Gemini call surface) are best-effort and may need adjustment by whoever owns that provider.

## Adding a new model

Don't touch the runner. See `CONTRIBUTING.md`.
