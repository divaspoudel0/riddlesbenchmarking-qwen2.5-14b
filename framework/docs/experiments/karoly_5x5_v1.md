# Karoly's 5×5 Pilot Experiment — Setup & Run Guide

> **Status:** Working draft. Several items are still TBD pending team decisions (master prompt content, final subset selection, model assignments). Each TBD is explicitly marked below. The framework side is ready and tested.

## What this is

A small-scale evaluation proposed by Karoly to start producing comparable results across the team before the full benchmark run.

- **5 team-curated subsets × 5 models = 25 runs**
- **Subsets:** chosen from communities where team members are native or fluent speakers, so they can verify the model's answers afterward
- **Models:** each model is run by whichever team member has the API key for it
- **Master prompt:** one canonical English prompt, with cultural-context placeholders that get filled in per-row

Two distinct roles in this experiment:
- **Cultural lead** — the person who created the subset and can judge whether model answers are correct (Vinod for Tamil, Karoly for Hungarian, etc.)
- **Model runner** — the person who has the API key for a particular model and runs the framework against the 5 subsets

The same person can play both roles, but they're separate. You might be a cultural lead without being a model runner if you don't have an API key, and vice versa.

This experiment exercises the master prompt design before the full benchmark commits to it.

## Current status (June 7, 2026)

| Item                                          | Status                                                       | Owner             |
| --------------------------------------------- | ------------------------------------------------------------ | ----------------- |
| Framework with cultural-context injection     | ✅ Done (this PR)                                            | Vinod             |
| Pilot dataset (39 communities, 3,900 riddles) | ✅ Done                                                      | Vinod             |
| Master prompt draft                           | 📝 In progress, deadline **June 9, 23:59 AOE**               | Team — Google Doc |
| Final 5 subsets                               | 🟡 Partial — Hungarian + Tamil + Moroccan likely; 2 more TBD | Team              |
| Final 5 models                                | 🟡 TBD — pending team API-access mapping                     | Team              |
| Per-member assignments                        | 🟡 TBD                                                       | Team              |
| Run kickoff                                   | ⏳ After master prompt lands                                 | Team              |

## Tentative subset list (pending confirmation)

- **Hungarian** — cultural lead: Karoly. Latin script.
- **Tamil** — cultural lead: Vinod. Tamil script, Brahmi-derived.
- **Moroccan Arabic** — cultural lead: Abdellah (TBC). Arabic script.
- **TBD #4** — ideally a Cyrillic-script subset for script diversity.
- **TBD #5** — ideally a CJK or other Indic subset.

Henry is helping suggest the last two.

**Note:** the cultural leads above are who can verify the model's answers afterward. They are not necessarily the people running the models — that's whoever holds each model's API key.

## Before you start

You'll need three things:

1. **The repo cloned and installed.** If you haven't done this yet, follow [docs/getting-started.md](../getting-started.md), section "Setting Up Your Environment", steps 1–3. Verify with `uv run pytest` — all tests should pass.

2. **An API key for your assigned model.** Which environment variable you need depends on which model you've been assigned:

   | Model family                           | Environment variable                         |
   | -------------------------------------- | -------------------------------------------- |
   | OpenAI (GPT-series)                    | `OPENAI_API_KEY`                             |
   | Anthropic (Claude)                     | `ANTHROPIC_API_KEY`                          |
   | Google (Gemini)                        | `GOOGLE_API_KEY`                             |
   | OpenRouter (Qwen, DeepSeek, xAI, etc.) | `OPENROUTER_API_KEY`                         |
   | Local Hugging Face                     | (none needed; `uv sync --extra local` first) |

   Setup details for each are in [docs/getting-started.md](../getting-started.md) section "Setting Up Your Environment", step 2.

3. **The run config for your assignment.** A YAML file in `framework/configs/` matching your model. Existing examples:
   - `configs/openai_gpt55_high.yaml`
   - `configs/openrouter_qwen37max.yaml`
   - `configs/local_transformers_example.yaml`

   For the 5×5, a new config per assignment will be added (see "Configs for the 5×5" below — TBD once models are assigned).

## Step-by-step run instructions

From the repo root:

```bash
# 1. Make sure you're on the latest main
cd RiddlesBenchmarking
git checkout main
git pull

# 2. Verify your API key is set in this shell
echo "$OPENAI_API_KEY" | head -c 6    # or ANTHROPIC_API_KEY etc.
# Should print the start of your key, not blank

# 3. Run the framework with your assigned config
cd framework
uv run python -m riddles_framework.cli --config configs/YOUR_ASSIGNED_CONFIG.yaml
```

You'll see `Run complete: <some-uuid>` when it's done. Each run writes output to:

```
framework/runs/<run_id>/
  run_config.json       # the exact settings you used
  run_metadata.json     # aggregate stats
  results.jsonl         # one line per riddle, with the model's answer
  manifest.json         # final summary
```

**Important:** the `--config` file points at `../data_loading/pilot_dataset/pilot_dataset_v1.jsonl` by default. That's the full 39-community pilot. For the 5×5, your config will likely point at a filtered subset file. See "Filtering the dataset to a subset" below.

## Filtering the dataset to a subset

The 5×5 uses subsets of the pilot, not the whole dataset. Each team member runs on the 5 chosen communities (or just their own — TBD). For now, the filtering is manual:

```bash
# From framework/ directory:
python3 - <<EOF
import json
SUBSETS = {"hungarian_hungary", "tamil_india", "arabic_morocco",
           "TBD_4", "TBD_5"}     # update once finalized
with open("../data_loading/pilot_dataset/pilot_dataset_v1.jsonl") as f_in, \
     open("../data_loading/pilot_dataset/pilot_dataset_5x5.jsonl", "w") as f_out:
    for line in f_in:
        if not line.strip(): continue
        row = json.loads(line)
        if row["community"] in SUBSETS:
            f_out.write(line)
print("Done.")
EOF
```

Then point your config's `dataset_path:` at `../data_loading/pilot_dataset/pilot_dataset_5x5.jsonl`.

**TBD:** once subsets are finalized, this filtered file should be committed to the repo so everyone runs against the exact same input.

## What success looks like

After your run completes, sanity-check:

```bash
# How many results were produced?
LATEST=$(ls -td framework/runs/*/ | head -1)
wc -l "$LATEST/results.jsonl"
# Expected: 500 for the full 5×100 subset, or 100 if you ran on just your own community

# How many failed?
python3 -c "
import json, sys
status_counts = {}
with open('$LATEST/results.jsonl') as f:
    for line in f:
        s = json.loads(line)['status']
        status_counts[s] = status_counts.get(s, 0) + 1
for s, n in sorted(status_counts.items()):
    print(f'  {s}: {n}')
"
# Expected: mostly 'success', minimal 'error' or 'refusal'
```

If you see many `error` or `refusal` statuses, something's wrong — see Troubleshooting.

## If something goes wrong

| Symptom                               | Likely cause                                                          | Fix                                                                                                                        |
| ------------------------------------- | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `No module named 'riddles_framework'` | Not installed, or wrong directory                                     | `cd framework && uv sync`                                                                                                  |
| `API key not found` / 401 errors      | Env var not set in this shell                                         | `echo $OPENAI_API_KEY` should print your key, not blank. Set it with `export`.                                             |
| `UnsupportedConfigurationError`       | Config requests something the model doesn't declare in `capabilities` | Check your config's `capabilities` block; either flip the flag (if the model really does support it) or change the request |
| `Duplicate riddle_id`                 | Dataset has duplicates — shouldn't happen with the merged pilot       | Ping Vinod, this is a data-side issue                                                                                      |
| Many `status: error` in results       | API quota, network, rate limit, or invalid model name                 | Check the `error_message` in `results.jsonl`; most issues are visible there                                                |
| Many `status: refusal` in results     | Model is refusing — interesting and probably worth noting             | Not a bug per se; the framework's heuristic only catches clear policy refusals                                             |

For framework or config issues: **ping Vinod** in `#multicultural-riddles-benchmark`.

For master prompt or methodology questions: discuss in the team Discord, since these are collective decisions.

## After the run

1. **Look at a few sample results** to sanity-check they look reasonable. The first 5 lines of `results.jsonl` is enough.

2. **Share your output.** TBD: the team will decide whether to upload `results.jsonl` to a shared Drive folder, push it to a results branch in the repo, or just share by Discord DM. Once the master prompt lands, this will be confirmed.

3. **Don't try to score answers yourself.** Scoring is T2.3 (Diana's task). The framework only produces raw model outputs; evaluation happens downstream.

4. **Flag anything surprising.** The 5×5 is a small experiment partly designed to surface issues with the master prompt or the framework. If you notice the model misunderstanding the language tag, the topic, or the script, write it up — that's the most useful signal we can produce from this run.

## What this experiment will NOT cover

- Automatic scoring of correctness — that's T2.3 (LLM-as-a-judge), separate
- Human evaluation — also separate
- All 39 communities — the full benchmark comes after, once 5×5 surfaces issues with the master prompt
- Comparison across models without controlling for cost / size — keep that in mind when interpreting

## Open questions for the team

These were not resolved as of June 7 and are worth a Discord thread:

1. **Where does `results.jsonl` get uploaded?** Drive folder, repo branch, or DMs?

---

_Document version 1, June 7, 2026. To be updated as the team finalizes decisions._
