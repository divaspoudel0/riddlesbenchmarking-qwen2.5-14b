from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request

import pandas as pd

from evals.llm_as_a_judge import (
    TARGET_MODELS,
    build_judge_messages,
    build_openrouter_payload,
    normalize_judge_instance,
    select_route,
)


def load_openrouter_key(env_path: Path) -> str:
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != "OPENROUTER_KEY":
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        return value
    raise RuntimeError("OPENROUTER_KEY not found in .env")


def main() -> int:
    api_key = load_openrouter_key(Path(".env"))
    os.environ["OPENROUTER_KEY"] = api_key
    model_limit = int(os.environ.get("MODEL_LIMIT", "20"))
    sample_size = int(os.environ.get("SAMPLE_SIZE", "20"))
    sample_seed = int(os.environ.get("SAMPLE_SEED", "42"))
    output_path = Path(
        os.environ.get(
            "OUTPUT_PATH",
            "judge/openrouter_eval_german_20_models_20_examples.jsonl",
        )
    )

    workbook_path = (
        "/Users/dianakozachek/Desktop/Cultural Riddles Benchmark [German_Germany].xlsx"
    )
    dataframe = pd.read_excel(workbook_path, sheet_name="Riddles")
    sample_size = min(sample_size, len(dataframe))
    random_generator = random.Random(sample_seed)
    sampled_indexes = sorted(random_generator.sample(range(len(dataframe)), sample_size))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, str]] = []
    output_path.write_text("", encoding="utf-8")
    tested_models = 0
    for model in TARGET_MODELS:
        route = select_route(model, "openrouter")
        if route is None or not route.model_name:
            continue
        if tested_models >= model_limit:
            break
        tested_models += 1

        for row_index in sampled_indexes:
            row = dataframe.iloc[row_index].to_dict()
            instance = normalize_judge_instance(
                row,
                culture="german_germany",
                row_index=row_index,
            )
            candidate = instance["reference_answer_original"]
            messages = build_judge_messages(instance, candidate_answer=candidate)
            payload = build_openrouter_payload(
                model,
                messages,
                temperature=0.0,
                max_output_tokens=300,
            )
            body = json.dumps(payload).encode("utf-8")
            req = request.Request(
                route.base_url,
                data=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://local.codex",
                    "X-Title": "RiddlesBenchmarking smoke test",
                },
                method="POST",
            )

            try:
                with request.urlopen(req, timeout=90) as response:
                    raw = response.read().decode("utf-8")
                parsed = json.loads(raw)
                content = parsed["choices"][0]["message"].get("content", "")
                result = {
                    "model": model.alias,
                    "row_number": str(instance["row_number"]),
                    "riddle_id": instance["riddle_id"],
                    "status": "ok",
                    "content": content,
                }
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                result = {
                    "model": model.alias,
                    "row_number": str(instance["row_number"]),
                    "riddle_id": instance["riddle_id"],
                    "status": f"http_{exc.code}",
                    "content": detail[:800],
                }
            except Exception as exc:  # noqa: BLE001
                result = {
                    "model": model.alias,
                    "row_number": str(instance["row_number"]),
                    "riddle_id": instance["riddle_id"],
                    "status": "error",
                    "content": str(exc),
                }

            results.append(result)
            with output_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(result, ensure_ascii=False))
                handle.write("\n")
            print(json.dumps(result, ensure_ascii=False), flush=True)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tested_models": len({r["model"] for r in results}),
        "sample_size": sample_size,
        "sample_seed": sample_seed,
        "calls": len(results),
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "output_path": str(output_path),
    }
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"summary": summary}, ensure_ascii=False))
        handle.write("\n")
    print(
        "SUMMARY",
        json.dumps(summary, ensure_ascii=False),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
