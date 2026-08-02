# Framework T2.2.1 — Plain Language Guide

## "What does this code actually do?"

---

## The Big Picture

Imagine you want to test how well different AI models solve cultural riddles. You have:

- A list of riddles from around the world
- Many different AI models you want to try
- Different ways to present the riddles (original language, English, with hints, without hints)

This framework is the **machine that runs those tests automatically**. You give it a config file saying "test GPT-5 with this riddle set in its original language" and it:

1. Loads the riddles
2. Builds the right prompts
3. Asks the AI model
4. Writes down the answers in a clean format for analysis

That's it. That's the whole job.

---

## The Main Parts Explained Simply

### 1. The Launcher (`cli.py` — "Command Line Interface")

Think of this as the **light switch**. It's what you run when you want to start a benchmark run.

```bash
uv run python -m riddles_framework.cli --config configs/openai_gpt55_high.yaml
```

**What it does in plain English:**

- Reads your configuration file (the YAML)
- Sets up the right adapter for the model you want to test
- Starts the BenchmarkRunner
- Tells you the run ID when it's done

You just point it at a config file and it does the rest.

---

### 2. The Configuration Files (`configs/*.yaml`)

These are **recipe cards** for different benchmark runs.

**Example:** `configs/openai_gpt55_high.yaml` might say:

- Use the OpenAI GPT-5.5 model
- Present riddles in their original language (not English)
- Don't use hints
- Ask for JSON formatted answers
- Turn on caching so we don't waste API calls

**You configure the benchmark by editing the YAML.** Want to test a different model? Change the model name. Want to use English riddles instead? Change `riddle_language_presented: english`.

The framework reads these settings and follows them exactly.

---

### 3. The Brains (`runner.py` — "BenchmarkRunner")

This is the **conductor of the orchestra**. It orchestrates everything that happens during a run.

**The sequence looks like this:**

```
1. Check if your configuration makes sense
    (if config is wrong, fail early — don't waste time)

2. Create a folder to store results


3. Load all the riddles from your dataset


4. Check if your chosen model can do what you're asking
    (can it handle JSON? Does it support reasoning?)

5. For each riddle:
   a. Build the right prompt
   b. Ask the AI model
   c. Record what the model said
   d. Move to the next riddle


6. Write a summary of what happened
```

**Why it's designed this way:**

- It fails fast on bad config (saves time)
- It records everything as it goes (if it crashes, you don't lose everything)
- It continues even if one riddle fails (one bad apple doesn't spoil the batch)

---

### 4. The Riddle Loader (`dataset_loader.py`)

This reads your **list of riddles** from a file.

The riddles come in a format called "JSONL" — which just means "one riddle per line, formatted as JSON." It's like a spreadsheet where each row is a riddle.

**For each riddle, it loads:**

- The riddle text (original language)
- The English translation (if available)
- A hint (if available)
- The correct answer
- Which community/language the riddle comes from

**It also checks:**

- No duplicate riddle IDs
- Required fields are present
- Data is valid

If there's a problem with the dataset, it tells you exactly which line has the issue.

---

### 5. The Prompt Builder (`prompts.py`)

This builds the **message you send to the AI model**.

A prompt isn't just "answer this riddle." It's a full instruction set:

- Who you are (an AI solving cultural riddles)
- What you're asking (the riddle itself)
- How you want the answer formatted (plain text? JSON?)
- Whether to include the hint

**The prompt builder does three things:**

1. **Chooses which riddle to use** — original language or English translation
2. **Adds the hint** (if the config says to use it)
3. **Wraps the instruction** with format requirements (e.g., "Return your answer as JSON: {"riddle_answer": "..."}")

**Adding a new prompt template** means creating a new YAML file. No code changes needed.

See section **5.5** below for how templates can include language/community/topic/script context automatically.

---

### 5.5. Cultural Context Injection (new)

A cultural riddle needs context. A Moroccan Arabic riddle about food and a Tamil riddle about poetry are very different tasks. The framework injects this context automatically from each dataset row.

**How it works:** Templates include placeholders in curly braces. At runtime, the framework fills them in.

**Template (YAML):**

```yaml
instruction_text: |
  You are solving a cultural riddle from {community_display}.
  The riddle is written in {language_name} ({script_name}), and the topic is {topic}.

  Answer it. If you are not certain, honestly say so.
```

**Rendered prompt for a Moroccan riddle:**

```
You are solving a cultural riddle from Moroccan Arabic, Morocco.
The riddle is written in Arabic (Arabic script), and the topic is Arts.

Answer it. If you are not certain, honestly say so.
```

**For a Tamil riddle:**

```
You are solving a cultural riddle from Tamil, India.
The riddle is written in Tamil (Tamil script), and the topic is History.

Answer it. If you are not certain, honestly say so.
```

**Why this matters:** Without explicit script information, a model might respond in the wrong script. Moroccan Arabic can be written in Arabic script (formal) or in Latin script (informal Darija romanization). Telling the model which one removes the ambiguity. The same principle applies for Konkani (Devanagari vs Kannada vs Roman), Serbian (Cyrillic vs Latin), and other multi-script languages.

**Available placeholders:**

| Placeholder           | Example        | What it is                      |
| --------------------- | -------------- | ------------------------------- |
| `{language}`          | `tam`          | ISO 639-3 code from the dataset |
| `{language_name}`     | `Tamil`        | Readable language name          |
| `{community}`         | `tamil_india`  | Community key from the dataset  |
| `{community_display}` | `Tamil, India` | Curated readable form           |
| `{country}`           | `India`        | Country portion                 |
| `{script_iso}`        | `Taml`         | ISO 15924 script code           |
| `{script_name}`       | `Tamil script` | Readable script name            |
| `{topic}`             | `History`      | Riddle topic                    |
| `{riddle_text}`       | (the riddle)   | Useful for custom layouts       |
| `{hint_text}`         | (the hint)     | If hints are enabled            |

You don't have to use all of them. A template using just `{community_display}` and `{topic}` is fine. Templates that don't use any placeholders still work — the framework just renders the instruction as-is. This is backward compatible with older templates.

The shipped example `prompt_templates/riddle_with_cultural_context_v1.yaml` shows the full pattern. The team's eventual master prompt will likely build on the same approach.

---

### 6. The Model Adapters (`models/*.py`)

These are **translators** between the framework and the AI providers.

Each provider (OpenAI, Anthropic, Google, etc.) has its own way of being called. Instead of hard-coding all of them into the main code, each provider gets its own adapter:

| Adapter                         | Provider           | What it does                                |
| ------------------------------- | ------------------ | ------------------------------------------- |
| `openai_adapter.py`             | OpenAI             | Calls OpenAI's API                          |
| `anthropic_adapter.py`          | Anthropic (Claude) | Calls Anthropic's API                       |
| `gemini_adapter.py`             | Google (Gemini)    | Calls Google's API                          |
| `openrouter_adapter.py`         | OpenRouter         | Routes to various models through OpenRouter |
| `transformers_local_adapter.py` | Local models       | Runs models on your own machine             |
| `dummy.py`                      | Dummy              | Always returns "dummy_answer" (for testing) |

**Why adapters?** If OpenAI changes their API, you only update `openai_adapter.py`. The rest of the framework doesn't care.

**Each adapter:**

1. Takes the framework's generic request
2. Translates it into the provider's specific API format
3. Calls the API
4. Translates the response back into a standard `GenerationResult` that the framework understands

---

### 7. The Model Registry (`registry.py` + `factory.py`)

This is the **matching system** that connects "I want to use OpenAI" with "here's the OpenAI adapter."

Instead of hardcoding "use OpenAI adapter for OpenAI," the framework keeps a registry:

```
"dummy:local"           → DummyModel
"openai:direct_api"     → OpenAIAdapter
"anthropic:direct_api"  → AnthropicAdapter
"google:direct_api"     → GeminiAdapter
"qwen:openrouter"       → OpenRouterAdapter
"xai:openrouter"        → OpenRouterAdapter
"openrouter:openrouter" → OpenRouterAdapter
"local:local"           → LocalTransformersAdapter
"vllm:vllm"             → VLLMAdapter
```

When you say `provider: openai` and `access_pattern: direct_api`, it looks up the right adapter in the registry.

**This makes it easy to add new providers:** Just register a new adapter. No need to edit the factory.

---

### 8. The Cache System (`cache_clients.py`)

This is an **optional shortcut** to avoid repeated API calls.

When caching is enabled:

- The first time you ask a question, it calls the API and saves the answer
- The next time you ask the same question, it returns the cached answer instantly
- You only pay for unique prompts

**Why use it?**

- Faster iteration on prompts (re-run without re-calling)
- Cheaper during development
- Reproducible results

**How it works:** Each adapter can use a "CacheSaver" version of the client that intercepts calls and checks the cache first.

**Getting results faster and cheaper:** the runner sends requests one at a time.
To get a run's results much faster — concurrently, or via the providers' offline
Batch APIs (OpenAI / Anthropic / Gemini, which are also ~50% cheaper) — fill the
cache first, then run normally for instant cache hits:
`python -m riddles_framework.batch.fill --config <cfg>`. See
[`../src/riddles_framework/batch/README.md`](../src/riddles_framework/batch/README.md).

---

### 9. The Writers (`writers.py`)

This saves everything to **your hard drive** in a clean, organized way.

Every run creates a folder like `runs/abc123/` with:

| File                | What's in it                                          |
| ------------------- | ----------------------------------------------------- |
| `run_config.json`   | The exact settings you used (so you can reproduce it) |
| `run_metadata.json` | Summary stats (how many succeeded, failed, skipped)   |
| `results.jsonl`     | One line per riddle with the model's answer           |
| `manifest.json`     | Final status and counts                               |

**`results.jsonl` is the main output.** Each line contains:

- The riddle that was asked
- The model input (the exact prompt sent)
- The model output (the answer)
- Timing information
- Error messages (if any)
- All configuration details (so you can understand the result without looking at other files)

---

### 10. The Data Structures (`schemas.py`)

These are **templates** that define what information moves through the system.

Think of them as standardized forms:

- `BenchmarkInstance` — one riddle with all its metadata
- `ModelSpec` — describes a model (name, provider, capabilities)
- `RunConfig` — everything you need to run one benchmark
- `GenerationResult` — what a model call returned
- `InstanceResult` — a complete record of one test

**Why bother with all these definitions?** So every piece of code can talk to every other piece without confusion. Everyone agrees on what a "riddle" looks like, what a "model" looks like, etc.

---

### 11. The Constants (`constants.py`)

These are **the vocabulary** — all the valid values for things.

Instead of writing "success" and "error" as random strings everywhere, they're defined once:

```python
class GenerationStatus:
    SUCCESS = "success"
    ERROR = "error"
    EMPTY = "empty"
    REFUSAL = "refusal"
    SKIPPED = "skipped"
```

This way, if you see `status: "refusal"` in the output, you know exactly what it means. It's also easier to add new statuses in one place.

---

### 12. The Exceptions (`exceptions.py`)

These are **named error types** so you can handle different problems differently.

Instead of just "something went wrong," you get:

- `DatasetValidationError` — the riddle list has a problem
- `UnsupportedConfigurationError` — your config asks for something the model can't do
- `PromptBuildError` — the framework couldn't build a prompt for a riddle
- `ConfigError` — the YAML file is malformed

This lets code react appropriately: some errors should stop the run, others should skip that one riddle and continue.

---

## How It All Fits Together

```
You run:  python -m riddles_framework.cli --config my_config.yaml
                │
                ▼
        ┌──────────────────┐
        │    cli.py       │  ← Reads config, registers adapters, starts runner
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │  BenchmarkRunner │  ← The conductor
        └────────┬─────────┘
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
┌────────────┐ ┌──────────┐ ┌────────────┐
│   Load     │ │  Build   │ │  Call      │
│  riddles   │ │  prompt  │ │  model     │
│            │ │          │ │            │
│ dataset_   │ │ prompts  │ │ (via       │
│ loader.py  │ │ .py      │ │  adapter)  │
└────────────┘ └──────────┘ └────────────┘
                                  │
                                  ▼
                          ┌──────────────┐
                          │    Write     │
                          │   results    │
                          │              │
                          │ writers.py  │
                          └──────────────┘
                                  │
                                  ▼
                          runs/<run_id>/
                            ├── run_config.json
                            ├── run_metadata.json
                            ├── results.jsonl
                            └── manifest.json
```

---

## Key Concepts in Plain English

### What is a "benchmark condition"?

It's just a combination of two choices:

1. **Language:** Do you show the riddle in its original language (e.g., Hindi) or in English?
2. **Hint:** Do you include the hint or not?

Combining these gives you four conditions:

- Original language, no hint
- Original language, with hint
- English, no hint
- English, with hint (this one is blocked — see below)

### What is a "provider" vs. "access pattern"?

- **Provider** is the company whose AI you're using: OpenAI, Anthropic, Google, etc.
- **Access pattern** is how you reach them: direct API call, through OpenRouter (a gateway service), or running locally on your own machine.

You might use the same provider through different access patterns (e.g., OpenAI direct vs. OpenAI through OpenRouter).

### What is "temperature"?

It's how "random" the AI's answers are.

- **High temperature** (e.g., 0.9): More creative, varied answers. Good for brainstorming.
- **Low temperature** (e.g., 0.1): More predictable, focused answers. Good for factual tasks.
- **No temperature set** (or `null`): The AI uses its own default. Recommended for reasoning models because they can get stuck in loops at low temperature.

### What is "structured output"?

It means telling the AI to respond in a specific format (usually JSON).

Instead of:

```
The answer is "the moon"
```

You get:

```json
{ "riddle_answer": "the moon" }
```

This makes it much easier for computers to read and analyze the results. The framework defaults to JSON because it's cleaner for analysis.

### What is "refusal detection"?

Some AI models refuse to answer certain questions ("I can't help with that"). The framework has a simple heuristic to detect when a model refused — so those cases can be analyzed separately.

**Important:** It's conservative. It only flags clear policy refusals. It does NOT flag:

- "I don't know"
- "I cannot determine"

Why? Because those might be honest, correct answers that the benchmark wants to measure.

### What is "caching"?

Instead of calling the API every time, the system remembers answers you've seen before.

**Pros:** Faster, cheaper for repeated prompts
**Cons:** You won't see different answers if the model's behavior changes

---

## Common Tasks

### How do I run the framework?

```bash
# Test with dummy model (no API calls)
uv run python -m riddles_framework.cli --config configs/dummy.yaml

# Run with a real model
export OPENAI_API_KEY=your_key_here
uv run python -m riddles_framework.cli --config configs/openai_gpt55_high.yaml
```

### How do I test a different model?

Edit the YAML config file. Change:

- `provider` — "openai", "anthropic", etc.
- `provider_model_name` — the specific model string
- `api_key_env_var` — which environment variable holds your API key

### How do I change how riddles are presented?

In the YAML config:

- `riddle_language_presented: source` — original language
- `riddle_language_presented: english` — English translation
- `is_hint_provided: true` — include the hint
- `is_hint_provided: false` — no hint

### How do I add a new prompt template?

1. Create a new YAML file in `src/riddles_framework/prompt_templates/`
2. Set `template_id` and `template_version`
3. Write your instruction text
4. Use it in your config by setting `prompt_template_id` and `prompt_template_version`

See section 5.5 above if your template should include cultural context placeholders.

### How do I use cultural context placeholders in a template?

Write placeholders in curly braces. The framework fills them from each dataset row at runtime:

```yaml
template_id: my_template
template_version: v1
recommended_response_format: json
instruction_text: |
  Solve this riddle from {community_display}, written in {script_name}.
  Topic: {topic}.
```

Full list of placeholders is in section 5.5.

### How do I add support for a new provider?

1. Create a new file in `models/` (e.g., `my_provider_adapter.py`)
2. Implement the `Model` abstract base class
3. Register it in `cli.py`'s `register_builtin_adapters()` function

---

## What the Framework Does NOT Do

- It does **not score answers** — that's a separate task (T2.3)
- It does **not do human evaluation** — that's a separate task
- It does **not build datasets** — the riddles come from elsewhere
- It does **not resume interrupted runs** — if it crashes, you re-run from scratch (though caching helps)

---

## Setting Up Your Environment

Before you can run the framework on a real model, you need a Python environment and an API key for whichever provider you'll use.

### Step 1 — Install the framework

You need `uv` (the Python package manager this project uses). If you don't have it:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Then restart your shell.
```

Clone the repo and install:

```bash
git clone https://github.com/Cohere-Labs-Community/RiddlesBenchmarking
cd RiddlesBenchmarking/framework

# API-only install. Sufficient for OpenAI, Anthropic, Gemini, OpenRouter:
uv sync

# OR with local Hugging Face inference (installs torch + transformers):
uv sync --extra local
```

Verify the install:

```bash
uv run pytest
```

All tests should pass green. If any fail, something is wrong with the install — see Troubleshooting below.

### Step 2 — Set your API key

Each provider uses a different environment variable. **Never commit API keys to git.** Set them in your shell:

**OpenAI:**

```bash
export OPENAI_API_KEY="sk-..."
```

**Anthropic (Claude):**

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Google Gemini:**

```bash
export GOOGLE_API_KEY="..."
```

**OpenRouter** (covers Qwen, DeepSeek, xAI, and many others through one key):

```bash
export OPENROUTER_API_KEY="sk-or-..."
```

**Local Hugging Face models** - no API key needed. Just `uv sync --extra local` first, set `provider_model_name` and `local_cache_client_mode` in `configs/local_transformers_example.yaml`, and make sure you have enough RAM/disk for the model. Use `batch_mode: true` with `batch_size` for local batch generation, or `batch_mode: false` for serial runs. For GPU, set `model_params.model_load.device_map: auto`.

To make your key persist across shells, add the `export` line to `~/.zshrc` (macOS default) or `~/.bashrc` (Linux).

### Step 3 — Run a safe test

The dummy config doesn't call any real API but exercises the whole framework:

```bash
uv run python -m riddles_framework.cli --config configs/dummy.yaml
```

You should see `Run complete: <some-uuid>`. Look inside `runs/<that-uuid>/` for the output files.

For a cultural-context smoke test:

```bash
uv run python -m riddles_framework.cli --config configs/dummy_cultural_context.yaml
```

### Step 4 — Run on a real model

Pick a real config (e.g. `configs/openai_gpt55_high.yaml`), confirm your API key is set, and run:

```bash
uv run python -m riddles_framework.cli --config configs/openai_gpt55_high.yaml
```

For coordinated team runs (such as Karoly's 5×5 test), the team will share specific configs. You only need your provider's API key set.

### Troubleshooting

- **`No module named 'riddles_framework'`** — Did you run `uv sync`? Are you in the `framework/` directory?
- **`API key not found` or 401** — Check that the variable is set in the same shell you're running the command from. `echo $OPENAI_API_KEY` (or equivalent) should print your key.
- **`UnsupportedConfigurationError`** — Your config asks the model for a feature it doesn't declare in `capabilities`. Either change the config or the model's capabilities entry.
- **`Duplicate riddle_id`** — The pilot dataset has duplicate IDs. Ping the data team; the framework's strict check is doing its job.

---

## Glossary for Non-Technical Readers

| Term                 | Plain English                                                                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Adapter**          | A translator that makes the framework work with different AI providers                                                                     |
| **Benchmark**        | A test to measure how well AI models perform on a specific task                                                                            |
| **Cache**            | Storage of previous API responses so you don't need to call again                                                                          |
| **Config**           | A settings file that tells the framework what to do                                                                                        |
| **Cultural context** | Language, community, country, topic, and script information injected into prompts so the model knows what kind of riddle it's answering    |
| **Framework**        | The main code system that ties everything together                                                                                         |
| **Instance**         | One riddle being tested (one "test case")                                                                                                  |
| **ISO 639-3**        | International standard for 3-letter language codes (`tam` = Tamil)                                                                         |
| **ISO 15924**        | International standard for 4-letter script codes (`Taml` = Tamil script, `Arab` = Arabic script, `Latn` = Latin script)                    |
| **JSON / JSONL**     | A data format that's easy for computers to read. JSONL = one JSON per line.                                                                |
| **Model**            | An AI system (like GPT-5, Claude, Gemini)                                                                                                  |
| **Placeholder**      | A `{name}` token inside a prompt template that the framework fills in from each riddle (e.g. `{community_display}` becomes `Tamil, India`) |
| **Provider**         | The company that provides the AI (OpenAI, Anthropic, Google, etc.)                                                                         |
| **Prompt**           | The message sent to the AI model                                                                                                           |
| **Registry**         | A list connecting provider names to their adapters                                                                                         |
| **Run**              | One complete benchmark execution                                                                                                           |
| **Schema**           | A template defining what data looks like                                                                                                   |
| **Script**           | The writing system a language uses (Arabic, Latin, Devanagari, etc.)                                                                       |
| **Template**         | A reusable prompt design stored as a YAML file                                                                                             |

---

_Plain language guide for Framework T2.2.1 — designed to be readable by anyone on the team._
