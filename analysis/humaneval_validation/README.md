# Human-eval validation

[`humaneval_validator_script.py`](humaneval_validator_script.py) checks the
human-evaluation workbooks before they are used for analysis. It catches the
data-quality problems that would otherwise silently skew human-vs-model
agreement.

## Checks

- Required columns (`Annotator Name`, `Score (0-3)`, `Error Type`) are present
  and non-null on both the main and extra sheets.
- Rows with `Error Type` = `0.4 - Other (add note)` / `2.4 - Other (add note)`
  have a non-empty `Validator Note`.

Problems are appended to `null_values.log` and `other_notes.log` in the working
directory.

## Input

Workbooks must be named `Human Eval <language>_<country>.xlsx` and placed in a
`HumanEval/` folder next to the script:

```
analysis/humaneval_validation/
├── humaneval_validator_script.py
├── requirements.txt
└── HumanEval/                 # not committed
    └── Human Eval Tamil_India.xlsx
```

## Run

```bash
cd analysis/humaneval_validation
python -m pip install -r requirements.txt
python humaneval_validator_script.py
```
