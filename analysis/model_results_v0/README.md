# Model Results Analysis (v0)

Results-side analysis of v0 model runs: loads run outputs, automatic judge
scores, and human evaluation data into one tidy frame, then generates the
paper/blog/slides figures.

Dataset-side analysis (riddle text features, validator distributions) lives
in `v1_analysis/` and `riddle_survey_analysis/`. This folder covers model
performance only.

## Data sources (not in git)

Populate `data/` manually from the shared Drive folder `RiddleBenchmarking`:

```
data/
  responses_v0/      <- Drive: Responses_v0 (one folder per model run)
  human_eval_v0/     <- Drive: Human Evaluation v0 (sheets as xlsx,
                        analysis_model_level.csv, human_eval_metadata.json)
```

Skip `Cache_v0`. Judge outputs are regenerated locally with `evals/`
rather than downloaded, so every model is scored by the same judge version.

Each run folder contains `manifest.json`, `run_config.json`,
`run_metadata.json`, and `results.jsonl`. Coverage varies per model
(see `completed_instances` in the manifest); accuracy denominators must
come from the manifest, not from row counts.

## Layout (planned)

- `load_results.py` - walk run folders, join metadata + judge outputs +
  human eval into one tidy frame (one row per riddle_id x model x condition)
- one script per figure, each a pure function `df -> fig`, styled via
  `analysis/style.py`
- `make_all.py` - regenerate every figure
- `figures/` - PDF (paper) and PNG (blog/slides) outputs
