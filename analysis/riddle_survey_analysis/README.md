# Riddle survey analysis

Analysis of the contributor reflection survey — how communities chose wildcard
topics, how confident and time-constrained contributors were, which resources
they used, and how difficult they found each topic.

## Inputs

The survey master sheet, exported as CSVs into [`csv/`](csv/):

```
csv/
├── [MCB]_Analysis_MasterSheet - reflection_form.csv   # main survey responses
├── [MCB]_Analysis_MasterSheet - Master_Codebook.csv
├── [MCB]_Analysis_MasterSheet - Codebook-1.csv
├── [MCB]_Analysis_MasterSheet - Code_Frequency_Reference.csv
├── [MCB]_Analysis_MasterSheet - Cross_Cutting_Themes.csv
└── [MCB]_Analysis_MasterSheet - Theme_Table.csv
```

## Outputs

PNG figures in [`figures/`](figures/): AI usage, confidence distribution,
local specificity, resources used, time per riddle, topic difficulty, wildcard
top codes, and per-language difficulty (Arabic, Bengali, Indonesian,
Portuguese).

## Run

```bash
cd analysis/riddle_survey_analysis
python run_all.py
```

Requires `pandas`, `matplotlib`, and `seaborn` (see
[`../requirements.txt`](../requirements.txt)). Figures use the shared style in
[`../style.py`](../style.py).
