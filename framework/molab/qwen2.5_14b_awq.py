# /// script
# requires-python = ">=3.10"
# dependencies = ["cachesaver==0.0.6", "PyYAML", "openai", "anthropic", "google-genai", "together"]
# ///
import marimo

__generated_with = "0.23.15"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _intro(mo):
    mo.md(
        r"""
        # Qwen2.5-Instruct-AWQ — Multicultural Riddles benchmark (molab)

        Runs a Qwen2.5 Instruct AWQ model (**14B** or **32B** — pick one in the
        dropdown below) over the Multicultural Riddles pilot dataset on the
        **molab** free tier. Execute the cells top to bottom:

        1. **Install** — framework deps + `transformers`, `accelerate`, `autoawq`.
        2. **Clone** — pull the benchmark repo into molab's persistent storage.
        3. **Load** — the AWQ model (once per session).
        4. **Smoke** — sanity pass on 25 riddles.
        5. **Run batches** `v0` (4400) / `v1` (400) / `v2` (1300) — resumable via CacheSaver.
        6. **Score / package / push** results to the GitHub repo.

        **molab tips**
        - Attach a free RTX GPU (96 GB VRAM) via the notebook *specs* button first.
        - Sessions last up to **12 h** and auto-shutdown after **90 min idle**.
        - Keep the **same notebook** across sessions so the repo clone + cache persist.
        - The run is interactive by design: progress prints here. Don't leave a batch
          cell running unattended for long, and re-run the batch cell to resume if the
          session dies (already-completed prompts hit the CacheSaver cache and are
          instant).
        """
    )
    return


@app.cell
def _stdlib_imports():
    import dataclasses
    import json
    import os
    import shutil
    import subprocess
    import sys
    import tarfile
    import time
    from pathlib import Path
    return (
        Path,
        dataclasses,
        json,
        os,
        shutil,
        subprocess,
        sys,
        tarfile,
        time,
    )


@app.cell
def _constants(mo):
    REPO_URL = "https://github.com/divaspoudel0/riddlesbenchmarking-e109e377.git"
    REPO_OWNER_REPO = "divaspoudel0/riddlesbenchmarking-e109e377"
    REPO_DIR = Path.home() / "riddlesbenchmarking"

    MODELS = {
        "Qwen/Qwen2.5-14B-Instruct-AWQ": {
            "config": "qwen2.5_14b_awq.yaml",
            "tag": "qwen2.5-14b",
        },
        "Qwen/Qwen2.5-32B-Instruct-AWQ": {
            "config": "qwen2.5_32b_awq.yaml",
            "tag": "qwen2.5-32b",
        },
    }
    model_choice = mo.ui.radio(
        options=list(MODELS),
        value="Qwen/Qwen2.5-14B-Instruct-AWQ",
        label="Hugging Face AWQ model",
    )

    DATASET_PATH = REPO_DIR / "data_loading/pilot_dataset/pilot_dataset_v1.jsonl"
    SMOKE_PATH = REPO_DIR / "data_loading/pilot_dataset/smoke_test_25.jsonl"
    CACHE_DIR = REPO_DIR / "framework/.cache/cachesaver"
    OUTPUT_ROOT = REPO_DIR / "framework/runs"
    PROGRESS_EVERY = 25
    TASK_ID = "ID"  # TODO: replace with your tracking-sheet ID
    return (
        CACHE_DIR,
        DATASET_PATH,
        MODELS,
        OUTPUT_ROOT,
        PROGRESS_EVERY,
        REPO_DIR,
        REPO_OWNER_REPO,
        REPO_URL,
        SMOKE_PATH,
        TASK_ID,
        model_choice,
    )


@app.cell
def _model_sel(MODELS, REPO_DIR, model_choice):
    """Resolve the selected model to its config + tag (read in a separate cell)."""
    MODEL_ID = model_choice.value
    MODEL_TAG = MODELS[MODEL_ID]["tag"]
    CONFIG_PATH = REPO_DIR / "framework/configs/benchmark_v0" / MODELS[MODEL_ID]["config"]
    return (CONFIG_PATH, MODEL_ID, MODEL_TAG)


@app.cell
def _install(mo, subprocess, sys):
    """Install Python packages (torch is preinstalled on molab). No-op if done."""
    core = [
        "cachesaver==0.0.6",
        "PyYAML",
        "openai",
        "anthropic",
        "google-genai",
        "together",
    ]
    ml = ["accelerate", "autoawq"]

    have_ml = False
    installed_version = None
    try:
        import transformers as _tr

        have_ml = True
        installed_version = _tr.__version__
    except Exception:
        pass

    needs_tr = not have_ml or int(installed_version.split(".")[0]) < 5
    if needs_tr:
        note = "installing/upgrading transformers (transformers >= 5 required for the AWQ `dtype=` kwarg)"
        if have_ml:
            note = f"upgrading transformers {installed_version} -> 5.x " + note.split("(")[1]
        mo.md(f"**Install note:** {note}")

    pkgs = list(core)
    if needs_tr:
        pkgs.append("transformers")
    pkgs += ml
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--prefer-binary", *pkgs],
        check=True,
    )

    import importlib.metadata as _md
    import cachesaver as cs
    import torch as torch_new
    import transformers as transformers_new

    try:
        import accelerate as accelerate_new

        acc_ver = accelerate_new.__version__
    except Exception:
        acc_ver = "?"

    version_report = {
        "torch": torch_new.__version__,
        "transformers": transformers_new.__version__,
        "accelerate": acc_ver,
        "cachesaver": _md.version("cachesaver"),
        "cuda_available": torch_new.cuda.is_available(),
    }
    version_report
    return version_report


@app.cell
def _clone_repo(os, REPO_DIR, REPO_OWNER_REPO, REPO_URL, subprocess):
    """Clone (or refresh) the benchmark repo into molab's persistent storage.

    The repo is private, so cloning needs a GitHub PAT (Content read+write).
    Set the `GITHUB_TOKEN` env var, or enter the same token in the PAT form
    (the push cell) before this cell runs.
    """
    _gh_token = os.environ.get("GITHUB_TOKEN") or ""
    if REPO_OWNER_REPO and _gh_token:
        auth_url = f"https://x-access-token:{_gh_token}@github.com/{REPO_OWNER_REPO}.git"
    else:
        auth_url = REPO_URL

    if not (REPO_DIR / ".git").exists():
        subprocess.run(["git", "clone", auth_url, str(REPO_DIR)], check=True)
    else:
        subprocess.run(["git", "-C", str(REPO_DIR), "fetch", "origin", "--prune"], check=True)
        subprocess.run(["git", "-C", str(REPO_DIR), "checkout", "main"], check=True)
        subprocess.run(
            ["git", "-C", str(REPO_DIR), "pull", "--ff-only", "origin", "main"],
            check=True,
        )
    head = subprocess.run(
        ["git", "-C", str(REPO_DIR), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    print(f"repo ready at {REPO_DIR} on {head.stdout.strip()}")
    return


@app.cell
def _framework_imports(REPO_DIR, sys):
    import os as _os

    _src = str(REPO_DIR / "framework/src")
    if _src not in sys.path:
        sys.path.insert(0, _src)
    _os.chdir(str(REPO_DIR / "framework"))

    from riddles_framework.factory import create_model
    from riddles_framework.prompts import load_prompt_template
    from riddles_framework.runner import BenchmarkRunner
    from riddles_framework.yaml_config import load_run_config_from_yaml

    print("framework importable from", _src)
    return (
        BenchmarkRunner,
        create_model,
        load_prompt_template,
        load_run_config_from_yaml,
    )


@app.cell
def _model_load(
    CACHE_DIR,
    CONFIG_PATH,
    MODEL_ID,
    create_model,
    load_prompt_template,
    load_run_config_from_yaml,
    time,
):
    """Load the selected AWQ model once. Re-run this cell (and the batch cells) to
    switch models after changing the dropdown."""
    import torch as _torch

    run_config = load_run_config_from_yaml(str(CONFIG_PATH))
    prompt_template = load_prompt_template(
        run_config.prompt_template_id, run_config.prompt_template_version
    )
    adapter_cfg = {
        "cache_enabled": run_config.cache_enabled,
        "cache_namespace": run_config.cache_namespace,
        "cache_dir": str(CACHE_DIR),
        "cache_backend": run_config.cache_backend,
        "local_cache_client_mode": run_config.local_cache_client_mode,
        "api_key_env_var": run_config.api_key_env_var,
        "base_url": run_config.base_url,
        "model_params": run_config.model_params,
        "batch_size": run_config.batch_size,
    }

    print(f"loading {MODEL_ID} …")
    t0 = time.time()
    model = create_model(run_config.model_spec, adapter_cfg)
    load_s = time.time() - t0

    if _torch.cuda.is_available():
        name = _torch.cuda.get_device_name(0)
        free, total = _torch.cuda.mem_get_info()
        print(
            f"model loaded in {load_s:.0f}s on {name} — "
            f"GPU mem free {free / 1e9:.1f} / {total / 1e9:.1f} GB"
        )
    else:
        print(
            f"model loaded in {load_s:.0f}s (CPU — attach a GPU from the notebook "
            "specs menu for a usable run)"
        )

    warm = model.generate(
        "What is 2+2? Answer with a number only.",
        max_output_tokens=8,
        response_format="free_form",
    )
    print("warm-up status:", warm.status, "|", str(warm.raw_response)[:60])
    return adapter_cfg, model, prompt_template, run_config


@app.cell
def _run_helper(PROGRESS_EVERY, dataclasses, time):
    def run_batch(batch_label, run_config, prompt_template, model, output_root):
        cfg = dataclasses.replace(run_config, run_batches=[batch_label])

        def on_progress(processed, total, completed, errored, skipped):
            if processed % PROGRESS_EVERY == 0 or processed == total:
                print(
                    f"[{batch_label}] {processed}/{total} "
                    f"ok={completed} err={errored} skip={skipped}",
                    flush=True,
                )

        runner = BenchmarkRunner(
            run_config=cfg,
            prompt_template=prompt_template,
            model=model,
            output_root=str(output_root),
            on_progress=on_progress,
        )
        t0 = time.time()
        run_id = runner.run()
        dt = time.time() - t0
        print(f"[{batch_label}] run complete: {run_id} in {dt / 60:.1f} min", flush=True)
        return run_id

    return run_batch


@app.cell
def _smoke(
    OUTPUT_ROOT,
    SMOKE_PATH,
    dataclasses,
    model,
    prompt_template,
    run_batch,
    run_config,
):
    """Sanity pass: 25 riddles, no hint. Verifies JSON answers come back."""
    import json as _json
    from pathlib import Path as _Path

    smoke_cfg = dataclasses.replace(
        run_config, dataset_path=str(SMOKE_PATH), run_batches=None
    )
    smoke_id = run_batch("smoke25", smoke_cfg, prompt_template, model, OUTPUT_ROOT)

    rows = []
    for p in sorted(_Path(OUTPUT_ROOT).glob(f"{smoke_id}/results.jsonl")):
        with p.open() as _fh:
            for _line in _fh:
                rows.append(_json.loads(_line))
    statuses = {}
    for row in rows:
        statuses[row["generation_status"]] = statuses.get(row["generation_status"], 0) + 1
    print("smoke statuses:", statuses)
    for row in rows[:3]:
        print("-", row["riddle_id"], "->", (row.get("raw_response") or "")[:90].replace("\n", " "))
    return smoke_id


@app.cell
def _batch_v0(OUTPUT_ROOT, model, prompt_template, run_batch, run_config):
    """Batch v0 — 4400 riddles, 44 communities."""
    run_id_v0 = run_batch("v0", run_config, prompt_template, model, OUTPUT_ROOT)
    return run_id_v0


@app.cell
def _batch_v1(OUTPUT_ROOT, model, prompt_template, run_batch, run_config):
    """Batch v1 — 400 riddles, 4 communities."""
    run_id_v1 = run_batch("v1", run_config, prompt_template, model, OUTPUT_ROOT)
    return run_id_v1


@app.cell
def _batch_v2(OUTPUT_ROOT, model, prompt_template, run_batch, run_config):
    """Batch v2 — 1300 riddles, 13 communities."""
    run_id_v2 = run_batch("v2", run_config, prompt_template, model, OUTPUT_ROOT)
    return run_id_v2


@app.cell
def _summary(OUTPUT_ROOT, Path):
    """List every completed run and its status counts."""
    import glob as _glob
    import json as _json

    report = []
    for _manifest in sorted(_glob.glob(str(OUTPUT_ROOT / "*/manifest.json"))):
        with open(_manifest) as _fh:
            _m = _json.load(_fh)
        counts = {
            k: _m.get(k)
            for k in ("total_instances", "completed_instances", "skipped_instances", "error_instances")
        }
        report.append(
            (Path(_manifest).parent.name, _m.get("run_batches"), counts, str(Path(_manifest).parent))
        )
    for _rid, _batches, _counts, _run_dir in report:
        print(_rid, "| batches:", _batches, "|", _counts, "|", _run_dir)
    if not report:
        print("no runs yet — run the smoke / batch cells first")
    return report


@app.cell
def _score(OUTPUT_ROOT, REPO_DIR, Path, subprocess, sys):
    """Optional, free: deterministic heuristic scoring (no LLM, no API key)."""
    import glob as _glob

    results = sorted(_glob.glob(str(OUTPUT_ROOT / "*/results.jsonl")))
    scored = []
    if results:
        for results_file in results:
            print("== scoring", results_file)
            proc = subprocess.run(
                [sys.executable, "evals/reference_heuristic_judge.py", results_file],
                cwd=str(REPO_DIR),
                capture_output=True,
                text=True,
            )
            _out = proc.stdout if proc.stdout else proc.stderr
            print(_out[-2000:])
            scored.append(results_file)
    else:
        print("no results yet")
    return scored


@app.cell
def _package(
    CACHE_DIR,
    MODEL_TAG,
    OUTPUT_ROOT,
    REPO_DIR,
    TASK_ID,
    Path,
    json,
    shutil,
    tarfile,
):
    """Copy run artifacts into benchmark_results/<TASK_ID>_<MODEL_TAG>/ for submission."""
    import glob as _glob

    dest = REPO_DIR / "benchmark_results" / f"{TASK_ID}_{MODEL_TAG}"
    dest.mkdir(parents=True, exist_ok=True)

    placed = {}
    for _manifest in sorted(_glob.glob(str(OUTPUT_ROOT / "*/manifest.json"))):
        with open(_manifest) as _fh:
            _m = json.load(_fh)
        _batches = tuple(_m.get("run_batches") or ())
        if _batches in placed:
            continue
        placed[_batches] = Path(_manifest).parent

    for _batches, _run_dir in placed.items():
        _label = "_".join(_batches) if _batches else "all"
        out = dest / _label
        out.mkdir(parents=True, exist_ok=True)
        for _f in ("results.jsonl", "run_config.json"):
            _src = _run_dir / _f
            if _src.exists():
                shutil.copy(_src, out / _f)
        print(f"copied {_run_dir.name} ({_label}) -> {out}")

    cache_tgz = dest / "cache.tgz"
    if CACHE_DIR.exists() and not cache_tgz.exists():
        with tarfile.open(cache_tgz, "w:gz") as tar:
            tar.add(CACHE_DIR, arcname="cachesaver")
        print("cache tarball:", cache_tgz)
    print("package dir:", dest)
    return dest


@app.cell
def _token_form(mo):
    """Enter a fine-grained GitHub PAT (contents: write). Submit to store it for the push cell."""
    token_form = mo.ui.form(
        mo.ui.text(label="GitHub PAT (contents: write)", kind="password"),
        label="Submit token",
        bordered=False,
    )
    token_form
    return token_form


@app.cell
def _push_github(MODEL_TAG, REPO_DIR, REPO_OWNER_REPO, subprocess, token_form):
    """Commit results and push them to GitHub. Re-runs only when the form above is submitted."""
    token = token_form.value
    if token is None:
        print("enter your PAT in the form above and submit it, then this cell runs")
    else:
        if isinstance(token, (list, tuple)):
            token = token[0] if token else None
        elif isinstance(token, dict):
            token = next(iter(token.values()))

        git = ["git", "-C", str(REPO_DIR)]
        status = subprocess.run(
            git + ["status", "--porcelain"], capture_output=True, text=True, check=True
        ).stdout.strip()
        if not status:
            print("nothing to commit — results are already pushed")
        else:
            subprocess.run(git + ["add", "-A"], check=True)
            subprocess.run(
                git
                + [
                    "-c",
                    "user.name=molab-runner",
                    "-c",
                    "user.email=molab-runner@users.noreply.github.com",
                    "commit",
                    "-m",
                    f"Qwen2.5-Instruct-AWQ ({MODEL_TAG}) molab benchmark results",
                ],
                check=True,
                capture_output=True,
            )
            push_url = f"https://x-access-token:{token}@github.com/{REPO_OWNER_REPO}.git"
            subprocess.run(git + ["push", push_url, "HEAD:main"], check=True, capture_output=True, text=True)
            print("pushed to", REPO_OWNER_REPO, "main")
    return


if __name__ == "__main__":
    app.run()
