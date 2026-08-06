#!/usr/bin/env python
"""Run a single pilot-dataset batch (v0/v1/v2) with the 14B AWQ model.

Designed to be launched as a DETACHED background process on a molab kernel
(subprocess.Popen with start_new_session=True): the marimo execute SSE stream
dies after ~1-2 min, but the background python survives and writes rows to
framework/runs/<run_id>/. Poll the run log / run dir across short execute calls.

Usage:
  python run_batch.py v0          # run the 'v0' run_batch on the 14B config
  python run_batch.py v1 <out>    # optional output_root override
  python run_batch.py v0 --resume # allow writing into an existing (cached) run

Uses the committed qwen2.5_14b_awq.yaml, which forces the gemm_triton AWQ
backend via quantization_config (necessary on molab: no CUDA compiler, so gptqmodel
auto-selecting Marlin would abort the load). CacheSaver caches each prompt so a
killed-and-resumed run fast-forwards over already-computed riddles.
"""
import sys
import os
import dataclasses
import json
import subprocess
import time

repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(repo)
if not os.path.isdir(os.path.join(repo, ".git")):
    raise SystemExit("run_batch.py must live inside the repo under framework/")

# Point imports at the framework source.
src = os.path.join(repo, "framework", "src")
sys.path_importer_cache.pop(src, None)
if src not in sys.path:
    sys.path.insert(0, src)
os.chdir(os.path.join(repo, "framework"))

# The marimo kernel persists across execute cells; purge stale framework/cachesaver
# modules so edits on disk are picked up.
for mod in [
    m for m in list(sys.modules) if m.startswith("riddles_framework") or m.startswith("cachesaver")
]:
    del sys.modules[mod]

import transformers.utils.import_utils as iu  # noqa: E402

try:
    iu.is_gptqmodel_available.cache_clear()
except Exception:
    pass

from riddles_framework import cli  # noqa: E402
from riddles_framework.factory import create_model  # noqa: E402
from riddles_framework.prompts import load_prompt_template  # noqa: E402
from riddles_framework.yaml_config import load_run_config_from_yaml  # noqa: E402
from riddles_framework.runner import BenchmarkRunner  # noqa: E402


def main() -> None:
    batch = sys.argv[1] if len(sys.argv) > 1 else "v0"
    if batch not in {"v0", "v1", "v2"}:
        raise SystemExit(f"unknown batch: {batch}")

    config_name = os.path.join(repo, "framework", "configs", "benchmark_v0", "qwen2.5_14b_awq.yaml")
    rc = load_run_config_from_yaml(config_name)
    pt = load_prompt_template(rc.prompt_template_id, rc.prompt_template_version)

    acfg = {
        "cache_enabled": rc.cache_enabled,
        "cache_namespace": rc.cache_namespace,
        "cache_dir": os.path.join(repo, "framework", ".cache", "cachesaver"),
        "cache_backend": rc.cache_backend,
        "local_cache_client_mode": rc.local_cache_client_mode,
        "api_key_env_var": rc.api_key_env_var,
        "base_url": rc.base_url,
        "model_params": rc.model_params,
        "batch_size": rc.batch_size,
    }

    print("BATCH_START", batch, flush=True)
    model = create_model(rc.model_spec, acfg)
    print("MODEL_READY", flush=True)

    cfg = dataclasses.replace(
        rc,
        dataset_path=os.path.join(repo, "data_loading", "pilot_dataset", "pilot_dataset_v1.jsonl"),
        run_batches=[batch],
    )

    def on_progress(p, t, c, e, s):
        if p % 25 == 0 or p == t:
            print(f"[{batch}] {p}/{t} ok={c} err={e} skip={s}", flush=True)

    runner = BenchmarkRunner(
        run_config=cfg,
        prompt_template=pt,
        model=model,
        output_root=os.path.join(repo, "framework", "runs"),
        on_progress=on_progress,
    )
    t0 = time.time()
    run_id = runner.run()
    manifest = json.load(open(os.path.join(repo, "framework", "runs", run_id, "manifest.json")))
    print(
        "BATCH_DONE",
        batch,
        "run",
        run_id,
        "min:",
        round((time.time() - t0) / 60, 2),
        "manifest",
        {k: manifest.get(k) for k in ("total_instances", "completed_instances", "error_instances")},
        flush=True,
    )


if __name__ == "__main__":
    main()