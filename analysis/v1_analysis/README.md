# V1 dataset analysis

Dataset-side analysis of the **v1 collection round**: consolidates contributor
workbooks, checks data quality and near-duplicate communities, and describes
riddle form, length, answer diversity, and validator coverage.

## Inputs

The contributor `.xlsx` workbooks plus `reference_sheet.xlsx`, by default read
from `~/Downloads/v1` (override with `--input-dir`). Workbooks must use the
standard contributor template columns.

## Outputs

- `csv/riddles_v1_consolidated.csv` — one row per riddle after cleaning.
- `csv/data_quality_notes.csv` — dropped duplicates, fallback sheets, backfilled
  translations, near-duplicate community pairs, etc.
- Per-culture summary tables in [`csv/`](csv/).
- Figures `fig1`–`fig9` in [`figures/`](figures/): wildcard themes, word counts,
  riddle form, length homogeneity, answer/lexical diversity, validator
  coverage, and validation outcomes.

## Run

```bash
cd analysis/v1_analysis
python run_all.py --input-dir /path/to/v1/workbooks
```

Requires `pandas`, `matplotlib`, `seaborn`, and `wordfreq` (see
[`../requirements.txt`](../requirements.txt)).
