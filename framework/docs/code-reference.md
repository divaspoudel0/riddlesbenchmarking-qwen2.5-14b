# Framework T2.2.1 — Multicultural Riddles Benchmark Framework

## Code Documentation Guide

---

## Overview

Framework T2.2.1 is the **benchmarking execution engine** for the Multicultural Riddles project. Its job is simple but critical: load riddles from a dataset, build prompts for a given experimental condition, run a model through a stable interface, and write standardized results that downstream analysis can consume.

This document explains every piece of code — what it does, why it exists, and how it all fits together.

> **Important scope note:** The framework does NOT score answers, do human evaluation, or build datasets. It only runs models and produces structured output.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (cli.py)                            │
│  Parses YAML config → Registers adapters → Creates runner       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BenchmarkRunner (runner.py)                  │
│  Orchestrates the full run: validation → loop → write           │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐    ┌────────────────┐    ┌──────────────────┐
│ Dataset Loader│    │ Prompt Builder  │   │ Model Interface   │
│ (loads JSONL) │    │ (builds prompt) │   │ (Model ABC +      │
│               │    │                 │   │  adapter per      │
│               │    │                 │   │  provider)        │
└───────────────┘    └────────────────┘    └──────────────────────┘
                                                    │
                              ┌──────────┬──────────┼──────────┬──────────┐
                              ▼          ▼          ▼          ▼          ▼
                        OpenAI    Anthropic    Gemini   OpenRouter  Local HF
                        Adapter   Adapter      Adapter  Adapter      Adapter

                               │
                               ▼
                    ┌─────────────────────┐
                    │  RunWriter (writers.py)  │
                    │  Writes: results.jsonl   │
                    │        run_config.json   │
                    │        run_metadata.json │
                    │        manifest.json     │
                    └─────────────────────────┘
```

---

## File-by-File Guide

### 1. `constants.py` — All the Enums in One Place

**What it does:** Defines the shared vocabulary for the entire framework. Every status, format, and language option lives here.

**Key enums:**

```python
class GenerationStatus(str, Enum):
    SUCCESS     = "success"    # Model returned something
    ERROR       = "error"       # API call failed
    EMPTY       = "empty"      # Model returned nothing
    REFUSAL     = "refusal"     # Model refused the task
    SKIPPED     = "skipped"     # Skipped due to config or prompt error
    TIMEOUT     = "timeout"     # (Reserved for future use)
    UNSUPPORTED_CONFIG = "unsupported_config"  # Bad config combo caught early

class ResponseFormat(str, Enum):
    FREE_FORM   = "free_form"   # Plain text answer
    JSON        = "json"        # Structured JSON (default per project guidance)
    JSON_SCHEMA = "json_schema" # Strict JSON with schema constraint

class RiddleLanguagePresented(str, Enum):
    SOURCE   = "source"   # Present riddle in original language
    ENGLISH  = "english"  # Present riddle in English translation
```

**Why it exists:** Keeps all string literals in one place. If you need to check what values are valid, look here — not scattered across 20 files.

---

### 2. `exceptions.py` — Framework Errors

**What it does:** Defines all custom exceptions so callers can handle specific failures.

```python
DatasetValidationError       # Dataset row is invalid (missing field, duplicate ID, etc.)
UnsupportedConfigurationError # Model + config combination is invalid
PromptBuildError             # Prompt cannot be constructed for an instance
PromptTemplateNotFoundError   # Requested template file doesn't exist
ModelRegistrationError       # Adapter registration failed
ConfigError                  # YAML config is malformed
CacheClientError             # Cache client construction failed
```

**Pattern:** All inherit from `FrameworkError`. Catch specific ones to handle them differently.

---

### 3. `schemas.py` — Data Structures

This is the biggest file. Every dataclass represents a core concept.

#### `BenchmarkInstance`

Represents one riddle from the dataset.

```python
@dataclass
class BenchmarkInstance:
    riddle_id: str              # Unique ID for this riddle
    language: str               # e.g., "Hindi", "Yoruba"
    community: str              # e.g., "South Asia", "West Africa"
    topic: str | None           # e.g., "Food", "Nature"

    # The riddle itself
    riddle_original: str        # Original language version (REQUIRED)
    riddle_english: str | None  # English translation
    riddle_hint: str | None     # Optional hint text
    riddle_note: str | None     # Optional notes

    # Reference answer (what a good model should output)
    reference_answer_original: str  # Answer in original language
    reference_answer_english: str | None

    # Human validation metadata
    author_credit: str | None
    human_validator_name: str | None
    human_answer_original: str | None
    human_answer_score: str | None
    human_answer_comment: str | None
```

Key methods:

- `from_dict()` — factory to create from a JSON line
- `validate()` — checks required fields; raises `ValueError` if missing

#### `ModelSpec`

Describes a model independently of how you access it.

```python
@dataclass
class ModelSpec:
    model_name: str          # Human-readable: "GPT-5.5-high"
    model_id: str            # Namespaced: "openai/gpt-5.5-high"
    provider: str            # "openai", "anthropic", "google", etc.
    access_pattern: str      # "direct_api", "openrouter", "local"
    provider_model_name: str # Real provider string: "gpt-5.5-high"

    capabilities: ModelCapabilities  # What features does this model support?

    # Optional metadata
    size_label: str | None
    closed_source: bool | None
    notes: str | None
```

#### `ModelCapabilities`

Feature flags that determine what the framework allows:

```python
@dataclass
class ModelCapabilities:
    supports_reasoning: bool          # Can use reasoning mode?
    supports_search: bool             # Can use web search?
    supports_structured_output: bool  # Can return JSON?
    supports_batch: bool             # Can do batch API calls?
    supports_seed: bool              # Can set random seed?
```

**Why it matters:** The runner validates your config against these capabilities BEFORE touching the filesystem. If you try to use `response_format: json` on a model that doesn't support it, it fails fast with a clear error.

#### `PromptTemplate`

Holds a reusable prompt instruction. Loaded from YAML files.

```python
@dataclass
class PromptTemplate:
    template_id: str        # e.g., "riddle_basic"
    template_version: str    # e.g., "v1", "v2"
    instruction_text: str   # The actual instruction text

    # Informational only — actual format comes from RunConfig
    recommended_response_format: ResponseFormat | None
```

Has a `render()` method that builds the full prompt:

```python
def render(
    self,
    *,
    riddle_text: str,
    hint_text: str | None = None,
    substitutions: dict[str, str] | None = None,
) -> str
```

**Two rendering modes:**

1. **Legacy mode** — if the template's `instruction_text` doesn't use `{riddle_text}`, the framework prepends the standard RIDDLE:/HINT: blocks:

   ```python
   # With hint:
   f"{instruction}\n\nRIDDLE:\n{riddle_text}\n\nHINT:\n{hint_text}"

   # Without hint:
   f"{instruction}\n\nRIDDLE:\n{riddle_text}"
   ```

2. **Full-layout mode** — if the template uses `{riddle_text}` directly in `instruction_text`, the template controls placement and the framework does not prepend RIDDLE: blocks.

In either mode, the optional `substitutions` dict fills `{language}`, `{community}`, `{community_display}`, `{country}`, `{script_iso}`, `{script_name}`, `{topic}`, and any other placeholders the template uses. Unknown placeholders are left intact rather than raising `KeyError`, so templates can declare placeholders the caller doesn't always provide (e.g. `{topic}` when the row's topic is None). See `_safe_format` in `schemas.py` and `build_substitutions` in `prompts.py`.

#### `RunConfig`

The complete configuration for one run, loaded from a YAML file.

Key fields:

- `model_spec: ModelSpec` — which model
- `dataset_path: str` — path to JSONL dataset
- `prompt_template_id` + `prompt_template_version` — which prompt template
- `riddle_language_presented: RiddleLanguagePresented` — `source` or `english`
- `is_hint_provided: bool` — include the hint or not
- `reasoning_mode: str | None` — e.g., "low", "medium", "high" (model-specific)
- `search_enabled: bool` — enable web search if the model supports it
- `response_format: ResponseFormat` — default is JSON (project guidance)
- `temperature: float | None` — intentionally optional; None means use model default
- `model_params: dict[str, Any]` — arbitrary provider params merged last
- `cache_enabled: bool` — use CacheSaver?

#### `GenerationResult`

What a model call returns.

```python
@dataclass
class GenerationResult:
    raw_response: str | None
    status: GenerationStatus
    error_message: str | None

    # Metrics
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None

    # Reasoning artifact (if reasoning mode was used)
    reasoning_artifact: str | None
    reasoning_artifact_type: str | None

    # Provider-specific details
    provider_details: dict[str, Any] | None
```

#### `InstanceResult`

One row in `results.jsonl`. Captures everything about a single riddle-model run.

Includes:

- All run config fields (so results are self-contained)
- All instance metadata (language, community, topic)
- Reference answers (for downstream scoring)
- Model input (the actual prompt sent)
- Raw response from the model
- Timing and token counts

#### `RunMetadata`

Aggregate statistics for a run. Written to `run_metadata.json`.

---

### 4. `dataset_loader.py` — Loading the Dataset

**Function:** `load_benchmark_instances(jsonl_path: str | Path) -> list[BenchmarkInstance]`

**What it does:**

1. Reads the JSONL file line by line
2. For each line, parses JSON → creates `BenchmarkInstance` → validates it
3. Checks for duplicate `riddle_id` values (raises error if found)
4. Sorts results by: community → topic → source row number → riddle_id

**Validation rules** (per `BenchmarkInstance.validate()`):

- `riddle_id` must be present
- `language` must be present
- `community` must be present
- `riddle_original` must be present and non-empty
- `reference_answer_original` must be present and non-empty

**Error handling:** If any row is malformed, raises `DatasetValidationError` with the line number.

---

### 5. `prompts.py` — Building Prompts

**The three jobs:**

1. **Load templates from YAML files** in `prompt_templates/`
2. **Build cultural-context substitutions** from each instance (new in v1.1)
3. **Build the actual prompt string** for a given instance

#### Template Loading

```python
load_prompt_template(template_id: str, template_version: str) -> PromptTemplate
```

Looks for a YAML file matching both `template_id` and `template_version`. Raises `PromptTemplateNotFoundError` if not found.

**Adding a new template:** Drop a new YAML file in `prompt_templates/` with:

```yaml
template_id: riddle_uncertainty
template_version: v1
recommended_response_format: json
instruction_text: |
  Solve the following cultural riddle.
  Be honest if you are not certain.
```

No code change required.

#### Prompt Building Functions

**`build_condition_id()`** — Generates a readable condition identifier:

```python
# Examples:
build_condition_id(SOURCE, False)  → "source_no_hint"
build_condition_id(SOURCE, True)   → "source_with_hint"
build_condition_id(ENGLISH, False) → "english_no_hint"
```

**`get_presented_riddle_text()`** — Chooses which version of the riddle to use:

- If `SOURCE`: returns `instance.riddle_original`
- If `ENGLISH`: returns `instance.riddle_english` (raises if missing)

**`get_presented_hint_text()`** — Returns the hint if enabled, or `None`

**`build_substitutions(instance)`** — Builds the placeholder dict consumed by `PromptTemplate.render()`. Reads `language`, `community`, `topic` from the instance, then enriches with derived fields from `community_display.py`:

```python
def build_substitutions(instance: BenchmarkInstance) -> dict[str, str]:
    community = instance.community or ""
    return {
        "language":          instance.language or "",
        "language_name":     format_language_name(community),
        "community":         community,
        "community_display": format_community_display(community),
        "country":           format_country(community),
        "script_iso":        format_script_iso(community),
        "script_name":       format_script_name(community),
        "topic":             instance.topic or "(unspecified)",
    }
```

Missing fields use sensible placeholders (`""` for unknown, `"(unspecified)"` for missing topic) rather than raising. Templates that use only some placeholders work fine; the framework only substitutes what the template asks for.

**`build_prompt()`** — The main function. Orchestrates everything:

1. Gets the riddle text (source or English)
2. Gets the hint text (if enabled)
3. Wraps the instruction with response format requirements
4. Builds cultural-context substitutions from the instance
5. Renders through `PromptTemplate.render(..., substitutions=...)`

**Response format wrapping:**

```python
if format == JSON:
    instruction += '\nReturn only valid JSON in this format: {"riddle_answer": "your answer"}'

if format == JSON_SCHEMA:
    instruction += '\nReturn strict JSON with exactly this schema: {"riddle_answer": "string"}'
```

---

### 5.5. `community_display.py` — Cultural Context Mappings (new in v1.1)

**What it does:** Maps community keys (e.g. `arabic_morocco`) to human-readable names, ISO 15924 script codes, and readable script names. Used by `build_substitutions()` in `prompts.py` to fill template placeholders.

**Three tables:**

```python
COMMUNITY_DISPLAY: dict[str, str]
# "arabic_morocco" -> "Moroccan Arabic, Morocco"
# "tamil_india"    -> "Tamil, India"
# Curated for all 39 pilot communities. Fall-through uses titlecase.

COMMUNITY_TO_SCRIPT_ISO: dict[str, str]
# "arabic_morocco"     -> "Arab"
# "tamil_india"        -> "Taml"
# "hungarian_hungary"  -> "Latn"
# ISO 15924 codes per community.

SCRIPT_ISO_TO_NAME: dict[str, str]
# "Arab" -> "Arabic script"
# "Taml" -> "Tamil script"
# "Latn" -> "Latin script"
# Readable script names indexed by ISO 15924 code.
```

**Five helper functions:**

```python
format_community_display(community: str) -> str
# "arabic_morocco" -> "Moroccan Arabic, Morocco"
# Unknown -> titlecased fallback ("klingon_qonos" -> "Klingon, Qonos")

format_country(community: str) -> str
# "tamil_india" -> "India"

format_language_name(community: str) -> str
# "tamil_india" -> "Tamil"

format_script_iso(community: str) -> str
# "arabic_morocco" -> "Arab"
# Unknown -> "" (so template authors can see the gap)

format_script_name(community: str) -> str
# "arabic_morocco" -> "Arabic script"
# Unknown -> "(unspecified)"
```

**Why it exists:** Centralizes the curated knowledge about what each pilot community's name, country, and script should look like in prompt prose. The alternative would be sprinkling this logic across templates, configs, and adapters — each maintaining its own version with drift over time.

**Future work:** When the data_loading pipeline adds a per-row `script` field to the dataset schema (e.g. for workbooks where a contributor explicitly used a non-default script), the framework will prefer the per-row script over `COMMUNITY_TO_SCRIPT_ISO`. The current code is the fallback.

---

### 6. `registry.py` — Model Adapter Registry

**Problem it solves:** How do you add a new model provider without touching the core code?

**Solution:** A simple registry that maps `"{provider}:{access_pattern}"` → factory function.

```python
_MODEL_REGISTRY: dict[str, Callable[[ModelSpec, dict], Model]] = {}

def register_model_adapter(key: str, factory: Callable) -> None
def get_model_adapter_factory(key: str) -> Callable
def list_registered_adapters() -> list[str]
```

**Example registrations (from `cli.py`):**

```python
("dummy:local",          lambda spec, cfg: DummyModel(spec))
("openai:direct_api",    lambda spec, cfg: OpenAIAdapter(spec, cfg))
("anthropic:direct_api", lambda spec, cfg: AnthropicAdapter(spec, cfg))
("google:direct_api",    lambda spec, cfg: GeminiAdapter(spec, cfg))
("qwen:openrouter",      lambda spec, cfg: OpenRouterAdapter(spec, cfg))
("xai:openrouter",       lambda spec, cfg: OpenRouterAdapter(spec, cfg))
("openrouter:openrouter", lambda spec, cfg: OpenRouterAdapter(spec, cfg))
("local:local",          lambda spec, cfg: LocalTransformersAdapter(spec, cfg))
```

**To add a new adapter:** See `CONTRIBUTING.md`. The pattern is:

1. Create `models/my_provider_adapter.py` implementing `Model` ABC
2. Register it in `cli.py`'s `register_builtin_adapters()`

---

### 7. `factory.py` — Creating Model Instances

**Simple glue code:**

```python
def create_model(spec: ModelSpec, adapter_kwargs: dict | None = None):
    key = f"{spec.provider}:{spec.access_pattern}"
    factory = get_model_adapter_factory(key)
    return factory(spec, adapter_kwargs or {})
```

The `adapter_kwargs` passes through cache config, API key env var, base URL, etc.

---

### 8. `models/base.py` — The Model Interface

**Abstract base class** that all adapters must implement.

```python
class Model(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        max_output_tokens: int = 256,
        seed: int | None = None,
        reasoning_mode: str | None = None,
        search_enabled: bool = False,
        response_format: str = "json",
        model_params: dict[str, Any] | None = None,
    ) -> GenerationResult:
        raise NotImplementedError
```

**Non-abstract method:**

```python
def generate_batch(self, prompts: list[str], ...) -> list[GenerationResult]:
    # Default implementation: calls generate() for each prompt sequentially
    # Adapters can override with true batch API for efficiency
```

---

### 9. `models/dummy.py` — Dummy Model for Testing

**What it does:** Always returns a predictable response. Used for smoke testing the framework without hitting any real API.

```python
class DummyModel(Model):
    def generate(self, prompt, ...) -> GenerationResult:
        if response_format in {"json", "json_schema"}:
            return '{"riddle_answer": "dummy_answer"}'
        else:
            return "dummy_answer"
```

**Usage:**

```bash
uv run python -m riddles_framework.cli --config configs/dummy.yaml
```

---

### 10. Model Adapters — Provider-Specific Implementations

Each adapter wraps a specific provider's SDK and translates framework calls into provider API calls.

#### `models/openai_adapter.py` — OpenAI / Azure OpenAI

Wraps the OpenAI Python SDK.

**Key features:**

- Uses `response_format: {"type": "json_object"}` for JSON mode
- Passes `reasoning_effort` for reasoning models
- Passes `web_search: True` for search-enabled models
- Merges `model_params` last so user can override anything

#### `models/anthropic_adapter.py` — Anthropic Claude

Wraps the Anthropic SDK.

**Key features:**

- Enables extended thinking when `reasoning_mode` is set:
  ```python
  kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget_tokens}
  kwargs["temperature"] = 1  # Required for extended thinking
  ```
- `thinking_budget_tokens` defaults to `max_output_tokens // 2`
- Handles multiple content blocks (text blocks concatenated)

#### `models/gemini_adapter.py` — Google Gemini

Wraps `google-genai`.

**Key features:**

- Best-effort implementation — the API surface varies; adapter owner can refine
- `model_params["config"]` is handled specially (passes through as `config=` arg)

#### `models/openrouter_adapter.py` — OpenRouter (multi-provider gateway)

Wraps OpenAI-compatible API through OpenRouter.

**Key features:**

- Default base URL: `https://openrouter.ai/api/v1`
- Handles Qwen, xAI, DeepSeek, and any other provider routed through OpenRouter
- Uses OpenAI client under the hood

#### `models/transformers_local_adapter.py` — Local Hugging Face Models

Runs Hugging Face causal language models locally.

**Key features:**

- Without cache: creates `transformers.pipeline("text-generation", ...)`
- With cache: uses CacheSaver's sync local Transformers wrapper in `sync` mode; uses `AsyncHFTransformers` in `async` mode when that wrapper is available
- Greedy decoding by default (no sampling unless temperature is set)
- Loads a matching tokenizer for token counts and cached-output decoding
- Supports `seed` via `transformers.set_seed`
- Supports local batch generation when `batch_mode: true`; `batch_size` controls runner chunks and CacheSaver/local inference batching
- Uses `model_params.model_load` for Hugging Face load-time settings such as `device_map: auto` and `dtype: float16` (the legacy `torch_dtype` key is still accepted)

---





---

### 11. `cache_clients.py` — Optional Caching Layer

**What it does:** Factory functions that return either a standard SDK client or a CacheSaver-aware client based on `use_cache` flag.

```python
make_openai_client(use_cache: bool, **kwargs)
make_anthropic_client(use_cache: bool, **kwargs)
make_gemini_client(use_cache: bool, **kwargs)
make_openrouter_client(use_cache: bool, **kwargs)
make_transformers_client(use_cache: bool, **kwargs)
```

**When cache is enabled:**

- CacheSaver intercepts API calls
- Caches responses by prompt hash
- On cache hit: returns cached response without calling the API
- Useful for: debugging, iteration on prompt templates, resuming interrupted runs

**When cache is disabled:** Returns the standard SDK client.

---

### 12. `runner.py` — The Main Orchestrator

**Class:** `BenchmarkRunner`

**The `run()` method does everything:**

```
1. Validate run config (fail fast on invalid conditions)
2. Create output directory
3. Load all benchmark instances from dataset
4. Write run_config.json
5. Validate model capabilities against config
6. If validation fails: write metadata + manifest, return early
7. Load the prompt template
8. Build condition ID
9. For each instance:
   a. Build the prompt
   b. If prompt build fails: record as SKIPPED, continue
   c. Call model.generate()
   d. If generation fails: record as ERROR
   e. Record result to results.jsonl
10. Write run_metadata.json
11. Write manifest.json
12. Return run_id
```

**Key design decisions in the runner:**

1. **Fails fast on invalid config** — `english + hints` is rejected before any filesystem activity
2. **Model capability validation** — rejects unsupported feature combinations early
3. **Continues on per-instance failures** — one bad instance doesn't abort the whole run
4. **Results written incrementally** — `append_result()` writes one JSONL line at a time (resumable)
5. **All config echoed to output** — `run_config.json` is written so results are self-documenting

---

### 13. `writers.py` — Output File Management

**Class:** `RunWriter`

Manages the output directory structure:

```
runs/
  <run_id>/
    run_config.json      # The YAML config echoed back
    run_metadata.json     # Aggregate stats
    results.jsonl        # One InstanceResult per line
    manifest.json        # Final summary
```

**Methods:**

```python
write_run_config(data: dict)     # Writes once at start
write_run_metadata(data: dict)   # Writes once at end
append_result(data: dict)        # Writes one line per instance (streaming)
write_manifest(data: dict)       # Writes once at end
```

---

### 14. `yaml_config.py` — Loading Configuration

**Function:** `load_run_config_from_yaml(path: str) -> RunConfig`

Parses a YAML file into a `RunConfig` object.

**Key behavior:**

- `temperature: null` or omitted → `None` (use model default)
- `temperature: 0.0` → `0.0` (really zero)
- `model_params` must be a dict if provided
- `riddle_language_presented` is parsed into the `RiddleLanguagePresented` enum
- `response_format` defaults to `"json"`

---

### 15. `cli.py` — Entry Point

**The main command-line interface.**

**Usage:**

```bash
uv run python -m riddles_framework.cli --config configs/openai_gpt55_high.yaml
uv run python -m riddles_framework.cli --config configs/dummy.yaml --output-root my_runs
```

**What it does:**

1. Parse `--config` argument (required) and `--output-root` (default: `runs`)
2. Register all built-in adapters
3. Load the YAML config
4. Load the prompt template
5. Build adapter config (cache settings, API key env var, etc.)
6. Create the model (DummyModel or real adapter)
7. Create a `BenchmarkRunner` and call `run()`
8. Print the run ID

---

### 16. `utils.py` — Shared Utilities

**Functions:**

```python
make_uuid() -> str                    # Generate a UUID for run_id / instance_id
ensure_dir(path: Path) -> None         # Create directory (mkdir -p)
write_json(path: Path, data: dict)     # Write pretty-printed JSON
append_jsonl(path: Path, records)     # Append one or more JSON lines
getenv_required(name: str) -> str     # Get env var or raise ValueError
safe_int(value: Any) -> int | None    # Safely parse int (return None on failure)
looks_like_refusal(text: str) -> bool # Heuristic refusal detector
```

**`looks_like_refusal()` details:**

- English-only heuristic
- Only catches policy refusals ("I can't help with that")
- Does NOT tag honest uncertainty ("I don't know", "I cannot determine") — those are signals the benchmark wants to measure
- Conservative: better to miss a refusal than incorrectly tag honest behavior

---

### 17. `model_specs.py` — Example Model Specifications

**What it does:** Provides factory functions for common model configurations.

**Included specs:**

- `dummy_spec()` — the dummy test model
- `openai_gpt55_high_spec()` — OpenAI reasoning model
- `openai_gpt55_none_spec()` — OpenAI non-reasoning model
- `anthropic_claude_opus_thinking_spec()` — Anthropic with extended thinking
- `anthropic_claude_opus_spec()` — Anthropic standard
- `gemini_pro_preview_spec()` — Google Gemini
- `openrouter_qwen37max_spec()` — Qwen via OpenRouter
- `local_transformers_spec(model_name)` — Generic local model spec

**IMPORTANT:** These are scaffold placeholders. Before any production run, replace `provider_model_name` values with actual strings your team has API access to.

---

### 18. Prompt Templates

YAML files in `src/riddles_framework/prompt_templates/`:

#### `riddle_basic_v1.yaml`

```yaml
template_id: riddle_basic
template_version: v1
recommended_response_format: free_form
instruction_text: |
  Solve the following cultural riddle.
  Give only the final answer, ideally in 1 to 4 words.
```

#### `riddle_basic_v2.yaml`

```yaml
template_id: riddle_basic
template_version: v2
recommended_response_format: json
instruction_text: |
  Solve the following cultural riddle.
  Return your answer as a single short phrase.
  If you are not certain, do your best — but be concise.
```

#### `riddle_with_uncertainty_v1.yaml`

Custom template for handling uncertainty cases.

#### `riddle_with_cultural_context_v1.yaml` (new in v1.1)

Example template demonstrating cultural-context placeholder substitution. Used by `configs/dummy_cultural_context.yaml` for smoke tests.

```yaml
template_id: riddle_with_cultural_context
template_version: v1
recommended_response_format: json
instruction_text: |
  You are solving a cultural riddle from {community_display}.
  The riddle is written in {language_name} ({script_name}), and the topic is {topic}.

  Please answer the riddle. If you are not certain, do your best, but
  it is better to honestly say you do not know than to guess.
```

The team's eventual master prompt for the 5×5 test will likely build on this pattern — same placeholder vocabulary, refined wording.

---

## Configuration Files

### `configs/dummy.yaml` — Smoke Test Config

Used for testing the framework end-to-end without API calls.

Key settings:

- `provider: dummy` → uses `DummyModel` directly (no adapter)
- `response_format: free_form`
- `max_output_tokens: 64`

### `configs/dummy_cultural_context.yaml` — Cultural Context Smoke Test (new in v1.1)

Used for smoke-testing cultural-context substitution against the full pilot dataset. Same as `dummy.yaml` but with:

- `prompt_template_id: riddle_with_cultural_context`
- `prompt_template_version: v1`
- `response_format: json`

Lets you verify rendered prompts include the right language, community, topic, and script for each riddle without making any API calls.

### `configs/openai_gpt55_high.yaml` — Real Provider Config

Example of a real model run configuration.

Key settings:

- `reasoning_mode: high` → enables reasoning
- `response_format: json` → structured output
- `cache_enabled: true` → uses CacheSaver for reproducibility
- `model_params: {top_p: 0.95}` → passes custom params to the adapter

---

## Supported Benchmark Conditions

| Condition           | `riddle_language_presented` | `is_hint_provided` | Status                        |
| ------------------- | --------------------------- | ------------------ | ----------------------------- |
| `source_no_hint`    | `source`                    | `false`            | ✅ Supported                  |
| `source_with_hint`  | `source`                    | `true`             | ✅ Supported                  |
| `english_no_hint`   | `english`                   | `false`            | ✅ Supported                  |
| `english_with_hint` | `english`                   | `true`             | ❌ Not supported (fails fast) |

**Why `english_with_hint` is unsupported:** Hints are in the source language. Presenting an English riddle with a source-language hint creates a confusing/mixed condition that the project has not defined.

---

## Data Flow (End-to-End)

```
User runs:
  uv run python -m riddles_framework.cli --config configs/openai_gpt55_high.yaml

CLI:
  1. register_builtin_adapters()
  2. load_run_config_from_yaml("configs/openai_gpt55_high.yaml")
     → RunConfig object with all settings

  3. load_prompt_template("riddle_basic", "v2")
     → PromptTemplate with instruction text

  4. create_model(model_spec, adapter_cfg)
     → OpenAIAdapter with CacheSaver client

  5. BenchmarkRunner(run_config, prompt_template, model, output_root).run()

Runner.run():
  1. validate_run_config() → pass
  2. load_benchmark_instances("data_loading/pilot_dataset/pilot_dataset_v1.jsonl")
     → list[BenchmarkInstance]

  3. validate_model_capabilities(model, run_config) → pass
  4. build_condition_id(source, false) → "source_no_hint"

  For each instance:
    build_prompt(instance, template, prompt_config)
    → "Solve the following cultural riddle...\n\nRIDDLE:\n{riddle_original}\n
    Return only valid JSON: {"riddle_answer": "..."}"

    model.generate(prompt, temperature=None, ...)
    → GenerationResult(raw_response='{"riddle_answer":"..."}', status=SUCCESS, ...)

    _build_instance_result(instance, gen)
    → InstanceResult with all fields populated

    writer.append_result(result.to_dict())
    → Appends to results.jsonl

  5. write_run_metadata(metadata)
  6. write_manifest(summary)

Output:
  runs/<run_id>/
    run_config.json
    run_metadata.json
    results.jsonl      ← One JSON line per riddle instance
    manifest.json
```

---

## Important Design Decisions

### 1. Temperature is Optional

```python
temperature: float | None = None  # Not float = 0.0
```

Many reasoning models (OpenAI o-series, Anthropic thinking, DeepSeek R1) fall into degenerate loops at low temperature. The framework defaults to the model's built-in temperature unless you explicitly set it.

- `temperature: null` (or omitted) → model default applies
- `temperature: 0.0` → really zero temperature

### 2. Arbitrary Provider Parameters via `model_params`

Instead of adding a new field for every provider parameter (`top_p`, `frequency_penalty`, etc.), the YAML accepts a `model_params:` dict that flows verbatim into the API request, merged last so it overrides framework defaults.

```yaml
model_params:
  top_p: 0.95
  frequency_penalty: 0.1
  presence_penalty: 0.0
```

### 3. Structured Output is the Default

Per project guidance, JSON structured output is the default. Set `response_format: free_form` in YAML if you need plain text.

### 4. Prompt Templates are YAML Files

Adding a new prompt template requires no code change:

1. Create `prompt_templates/my_template_v1.yaml`
2. Set `template_id: my_template` and `template_version: v1` in your YAML config
3. The framework finds and uses it automatically

### 5. Refusal Detection is Conservative

The `looks_like_refusal()` heuristic only tags policy refusals ("I can't help with that"). It does NOT tag:

- "I don't know"
- "I cannot determine"
- "Not enough information"

These may reflect epistemically honest behavior that the benchmark wants to measure.

### 6. Cultural Context Injection (new in v1.1)

Templates opt into cultural-context injection via Python `str.format`-style placeholders. The framework substitutes values per-instance at render time:

```yaml
instruction_text: |
  You are solving a cultural riddle from {community_display}.
  The riddle is written in {language_name} ({script_name}), and the topic is {topic}.
```

**Why this design over alternatives:**

- **Backward compatible.** Templates without placeholders behave exactly as before (RIDDLE:/HINT: blocks prepended). No existing template breaks.
- **Templates declare what they need.** The framework provides a fixed vocabulary of placeholders; a template uses whichever subset it wants. Missing placeholders don't crash — `_safe_format` leaves them intact rather than raising `KeyError`.
- **Single source of truth.** All community-to-display, community-to-script, and script-to-name mappings live in `community_display.py`. Adding a new community is a single-file edit.
- **Per-row script TBD.** v1 uses one script per community. When the data_loading pipeline adds per-workbook script declarations, the framework can prefer the per-row value over the community default.

**Why ISO 15924 specifically:** It's the international standard for script codes (`Arab`, `Latn`, `Deva`, `Taml`, etc.). Using the standard means downstream tools (HuggingFace dataset cards, NLP libraries, paper references) all speak the same language about scripts.

This directly addresses three converging design conversations on the project: Tenney's consensus point #2 ("include language, cultural, and topic-specific context"), Abdellah's concern about Moroccan Arabic script ambiguity (Arabic vs Latin/Darija romanization), and Diana's preference for one canonical template with localization rather than per-language authoring.

---

## Known Limitations (v1)

1. **Refusal tagging is English-only and heuristic** — non-English refusals won't be tagged; the heuristic may miss edge cases. Downstream T2.3 / human eval will refine this.

2. **Provider model strings are placeholders** — `provider_model_name: gpt-5.5-high` must be replaced with actual strings your team has API access to before production runs.

3. **Resume mode not implemented** — if a run crashes mid-way, the entire run must be re-executed. Cache will short-circuit already-seen prompts, but `results.jsonl` starts fresh.

4. **Provider SDK surfaces evolve** — some adapter-level knobs (reasoning effort, web search toggles, Gemini config surface) are best-effort and may need adjustment.

---

## Glossary

| Term                    | Definition                                                                 |
| ----------------------- | -------------------------------------------------------------------------- |
| **Benchmark condition** | A specific combination of `riddle_language_presented` + `is_hint_provided` |
| **Condition ID**        | A readable string like `source_no_hint` identifying the condition          |
| **Provider**            | The company/service hosting the model (OpenAI, Anthropic, Google, etc.)    |
| **Access pattern**      | How you reach the model (direct API, OpenRouter, local, etc.)              |
| **Model spec**          | A description of a model including its capabilities                        |
| **Generation result**   | The output of a single model call                                          |
| **Instance result**     | A full record of one riddle-model run including config and metadata        |
| **CacheSaver**          | Optional caching layer for reproducible runs                               |
| **JSONL**               | JSON Lines — one JSON object per line (streaming-friendly format)          |
| **Cultural context**    | Language, community, country, topic, and script metadata injected per-row into prompts |
| **Placeholder**         | A `{name}` token inside a prompt template, substituted at render time      |
| **ISO 639-3**           | International standard for 3-letter language codes (`tam` = Tamil)         |
| **ISO 15924**           | International standard for 4-letter script codes (`Taml` = Tamil script)   |

---

_Documentation generated for Framework T2.2.1 — Multicultural Riddles Benchmark_
