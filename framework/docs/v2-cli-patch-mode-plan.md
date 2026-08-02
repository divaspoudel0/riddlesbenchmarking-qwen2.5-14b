# V2 CLI: patch-rerun mode — design plan

Status: proposal, for review. Goal: let a runner re-evaluate only specific
(corrected) riddles without rerunning the whole set or reopening a frozen
version, cheaply and reproducibly. Motivating case: a single corrected
riddle (e.g. `spanish_cuba_history_016`) needs fresh model answers without
a full campaign rerun.

## What the code already gives us

- Dataset rows carry `riddle_id` and `run_batch` (v0, v1, ...).
- `load_benchmark_instances(path, run_batches=...)` in `dataset_loader.py`
  loads the dataset and filters by batch. It already raises on an unknown
  batch and on duplicate riddle_ids.
- The runner builds one prompt per instance and routes generation through
  CacheSaver, keyed on prompt content within a namespace. So a changed
  riddle text is a different prompt = cache miss = fresh call; every
  unchanged riddle is a cache hit = free.
- `--run-batch` already scopes a run to one submission batch.

So the cache already solves cost. What is missing is a way to process
*only the changed riddles*, and to fold their new answers back into the
analysis cleanly.

## Why `--run-batch` alone is not enough

`--run-batch v2` reruns the whole v2 batch. If v2 is a batch of new
communities plus one corrected old riddle, that reruns all the new
communities too. For a single-riddle fix we want a surgical selector.

## Proposed CLI surface: `--riddle-id`

Mirror the existing `--run-batch` flag:

```bash
uv run python -m riddles_framework.cli --config <cfg> \
    --riddle-id spanish_cuba_history_016
# multiple: --riddle-id id_a id_b ...
# combinable with --run-batch (intersection)
```

Implementation is small and local:
- `cli.py`: add a `--riddle-id` arg (nargs="+"), pass into the run config.
- `dataset_loader.py`: add a `riddle_ids` filter next to the `run_batches`
  filter; same "empty match raises" guard, so a typo is caught rather than
  silently run as zero riddles.
- `runner`: no change; it just receives fewer instances.
- Output: a scoped `results.jsonl` with only the patched riddles, plus a
  `run_metadata.json` flag (`patch: true`, `patched_riddle_ids: [...]`,
  base namespace) so provenance is explicit.

Effect: only the changed riddle is processed (no serial loop over the
other ~4,399), only it can cost an API call, and the output is a small,
reviewable patch file.

## Change detection: manual first, auto later

- **Ship first (manual):** runner passes the ids they know changed
  (`--riddle-id ...`). Explicit, stateless, no failure modes.
- **Later (auto, optional):** store a per-riddle content hash in a
  manifest at build time; a `--only-changed` flag diffs the current
  dataset against the last manifest and selects changed ids
  automatically. More convenient, more moving parts. Defer unless
  corrections turn out to be frequent.

## The other half: folding the patch into analysis

A patch run yields a small `results.jsonl` for the corrected riddle. The
analysis loader must overlay it on the base run, replacing the stale rows
for that `riddle_id`. Proposed convention:

- Patch lands in its own folder, e.g. `<run>__patch_<date>/`.
- Loader rule: on a `riddle_id` collision between base and patch, newest
  wins (by run timestamp). The loader already keys on
  `(source_folder, riddle_id)`; this adds a "latest wins per riddle_id"
  overlay step.

This keeps the two halves decoupled: the framework writes a patch folder,
the analysis loader knows how to merge it. Neither blocks the other. The
loader change is owned on the analysis side.

## Guardrails

- Refuse a patch run whose `riddle_id` is not in the dataset (typo
  protection), mirroring the existing unknown-batch error.
- Record patch provenance in `run_metadata.json` (patched ids, base
  run_id, namespace).
- Patches apply to the current open version only, never a frozen one. A
  frozen version (v0) stays as-is; corrections re-run in the open version.

## Worked example: a single corrected riddle

1. Corrected source row is fixed at build time and tagged into the batch
   that will run next.
2. Each runner: `--config <their cfg> --riddle-id <the id>` against the
   shared cache. One API call per model.
3. Patch results land in a patch folder; analysis overlays them. No
   coordination round, no full rerun.

## Open questions

- Does v2 reuse the shared cache dir? (If yes, patch reruns are free
  except the changed prompt.)
- Folder naming convention for patch outputs (so the loader overlay can
  match it).
- Ship manual `--riddle-id` now and defer `--only-changed`, or build both?
- Should `--riddle-id` and `--run-batch` intersect, or is `--riddle-id`
  standalone enough for the fix use case?
