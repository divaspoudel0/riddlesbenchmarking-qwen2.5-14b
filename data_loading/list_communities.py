"""Generate COMMUNITIES.md: the language + community list and credits.

Reads the built pilot dataset and writes a human-readable index of every
community (language, collection round, riddle count) plus provisional
contributor credits pulled from the author_credit field. Rerun after each
build so the list stays in sync; the same content seeds the HuggingFace
dataset card.

Usage:
    python list_communities.py
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from export_huggingface import parse_contributors

HERE = Path(__file__).parent
DATASET = HERE / "pilot_dataset" / "pilot_dataset_v1.jsonl"
OUT = HERE / "COMMUNITIES.md"
OUT_CSV = HERE / "communities_and_credits.csv"


def readable(community: str) -> str:
    """tamil_india -> 'Tamil India' (canonical token kept in its own column)."""
    return community.replace("_", " ").title()


def main() -> None:
    rows = [json.loads(l) for l in DATASET.read_text().splitlines() if l.strip()]
    # Reuse the HF card's contributor parser so this list matches the card
    # (handles comma/slash/newline-joined names, backticks, case dupes).
    contributors = parse_contributors(pd.DataFrame(rows))

    comms: dict[str, dict] = {}
    for r in rows:
        c = r["community"]
        d = comms.setdefault(
            c, {"lang": r["language"], "batch": r["run_batch"], "n": 0}
        )
        d["n"] += 1

    n_comm = len(comms)
    n_lang = len({d["lang"] for d in comms.values()})
    by_round = Counter(d["batch"] for d in comms.values())
    round_str = ", ".join(f"{k}: {v}" for k, v in sorted(by_round.items()))

    lines = [
        "# Communities and languages",
        "",
        "Generated from `pilot_dataset/pilot_dataset_v1.jsonl` by "
        "`list_communities.py`. Do not edit by hand; rerun the script.",
        "",
        f"**{len(rows):,} riddles** across **{n_comm} communities** and "
        f"**{n_lang} languages** (ISO 639-3). Communities per collection "
        f"round: {round_str}.",
        "",
        "> Language counts treat regional dialects as distinct languages "
        "(e.g. Egyptian, Moroccan, Sudanese, Syrian, Lebanese, and Tunisian "
        "Arabic each count separately), since they are separate communities "
        "with distinct riddles. Select a round for evaluation with the "
        "`--run-batch` flag; the round lives in the `run_batch` column, not "
        "the filename.",
        "",
        "## Communities",
        "",
        "| Community (token) | Name | Language (ISO 639-3) | Round | Riddles |",
        "|---|---|---|---|---|",
    ]
    for c in sorted(comms, key=lambda x: (comms[x]["batch"], x)):
        d = comms[c]
        lines.append(
            f"| `{c}` | {readable(c)} | {d['lang']} | {d['batch']} | {d['n']} |"
        )

    lines += [
        "",
        "## Contributor credits (provisional)",
        "",
        "Names are pulled from the `author_credit` field and are provisional "
        "pending contributor confirmation before any public release.",
        "",
        "| Community | Contributors |",
        "|---|---|",
    ]
    for c in sorted(comms):
        authors = ", ".join(contributors.get(c, []))
        lines.append(f"| `{c}` | {authors or '—'} |")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}: {n_comm} communities, {n_lang} languages")

    # CSV for the attribution team to cross-check (one row per community).
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["community", "name", "language_iso", "run_batch",
                    "riddle_count", "contributors"])
        for c in sorted(comms):
            d = comms[c]
            w.writerow([c, readable(c), d["lang"], d["batch"], d["n"],
                        "; ".join(contributors.get(c, []))])
    print(f"Wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
