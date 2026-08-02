# Pilot Dataset — 5 Languages

A focused subset of `pilot_dataset_v1.jsonl` covering five target languages:
**Hungarian, Tamil, Moroccan Arabic, Russian, and Chinese**.

- File: `pilot_dataset_5lang.jsonl`
- Total riddles: 500 (100 per community)
- Derived from: `pilot_dataset_v1.jsonl` (built 2026-06-17T06:23:27Z)

Rows are copied **verbatim** from v1 — same schema, same field values, same
`instance_result_id` / `riddle_id` — so every row is traceable back to the full
dataset. No transformation is applied beyond the community filter.

## Coverage

| Language | Community | ISO 639-2/3 | Riddles |
| --- | --- | --- | --- |
| Hungarian | `hungarian_hungary` | `hun` | 100 |
| Tamil | `tamil_india` | `tam` | 100 |
| Moroccan Arabic | `arabic_morocco` | `ary` | 100 |
| Russian | `russian_russia` | `rus` | 100 |
| Chinese (Mandarin) | `chinese_china` | `zho` | 100 |

"Chinese" here means the `chinese_china` community only. The full dataset also
contains `chinese_simplified_china` (`zho`) and `cantonese_china` (`yue`); both
are intentionally excluded from this subset.

## Schema

Identical to v1 — see [`README.md`](README.md) for the full field-by-field
schema, design decisions, and known open questions.

## How to rebuild

This subset is a deterministic filter of v1 by `community`:

```bash
cd data_loading
python - <<'PY'
import json
from pathlib import Path
src = Path("pilot_dataset/pilot_dataset_v1.jsonl")
out = Path("pilot_dataset/pilot_dataset_5lang.jsonl")
keep = {"hungarian_hungary", "tamil_india", "arabic_morocco", "russian_russia", "chinese_china"}
with src.open(encoding="utf-8") as f, out.open("w", encoding="utf-8") as g:
    for line in f:
        if line.strip() and json.loads(line)["community"] in keep:
            g.write(line)
PY
```

To regenerate from the upstream contributor submissions instead, rebuild
`pilot_dataset_v1.jsonl` first (see [`README.md`](README.md) → "How to rebuild")
and re-run the filter above.
