# Benchmark results

Packaged benchmark outputs collected for submission and archiving. Each
subfolder is named after the model (or `<TASK_ID>_<MODEL_TAG>` when produced by
the molab notebook) and holds the run outputs plus a compressed copy of the
CacheSaver cache used to produce them.

```
benchmark_results/
└── qwen2.5-14b/
    ├── cache_v0.tgz     # cache for the v0 collection round
    ├── cache_v1.tgz     # cache for the v1 collection round
    └── cache_v2.tgz     # cache for the v2 collection round
```

## Raw runs vs. packaged results

- **Raw run artifacts** (the `results.jsonl` the framework writes) live under
  [`framework/runs/`](../framework/runs/). Those are the files you score with
  [`evals/`](../evals/).
- **`benchmark_results/`** is the archive/submission layer: it groups a model's
  runs and adds the compressed cache so the exact answers are reproducible
  without re-calling the provider.

The molab notebook ([`framework/molab/`](../framework/molab/)) has a *package*
cell that copies `results.jsonl` + `run_config.json` and writes `cache.tgz`
here automatically.

## Reproducing a run from a cache

```bash
# From the repo root
mkdir -p framework/.cache
tar -xzf benchmark_results/qwen2.5-14b/cache_v0.tgz -C framework/.cache
# Then run the matching config; identical prompts hit the cache instead of the model.
```

See [`framework/README.md`](../framework/README.md) and the
[batch guide](../framework/src/riddles_framework/batch/README.md) for cache
namespaces and details.
