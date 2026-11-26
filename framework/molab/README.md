# molab notebook — Qwen2.5 Instruct AWQ

[`qwen2.5_14b_awq.py`](qwen2.5_14b_awq.py) is a [marimo](https://marimo.io/)
notebook that runs the **Qwen2.5-14B / 32B Instruct AWQ** models over the pilot
dataset on the [molab](https://molab.marimo.io/) free tier. It is the
self-contained path used to produce the headline Qwen results in
[`benchmark_results/`](../../benchmark_results/).

## What the cells do

1. **Install** — framework deps plus `transformers`, `accelerate`, `autoawq`.
2. **Clone** — clone/refresh this repo into molab's persistent storage.
3. **Load** — load the selected AWQ model (pick 14B or 32B in the dropdown).
4. **Smoke** — sanity pass on `data_loading/pilot_dataset/smoke_test_25.jsonl`.
5. **Run batches** — `v0` (4,400), `v1` (400), `v2` (1,300); resumable via
   CacheSaver.
6. **Score / package / push** — optional heuristic scoring, then copy results
   and a cache tarball into `benchmark_results/` and push to GitHub.

## Using it

- Open the notebook on molab and attach a GPU from the **specs** menu first.
- Run the cells top to bottom. Sessions last up to 12 h and shut down after
  90 min idle; keep the same notebook so the clone and cache persist.
- Re-run a batch cell to resume after a disconnect — completed prompts hit the
  cache and are instant.
- The clone and push cells expect a GitHub token (`GITHUB_TOKEN` or the PAT
  form) with contents read/write access.

The model configs it reads live in
[`../configs/benchmark_v0/`](../configs/benchmark_v0/) (`qwen2.5_14b_awq.yaml`,
`qwen2.5_32b_awq.yaml`).
