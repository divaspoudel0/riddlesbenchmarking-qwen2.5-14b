# Analysis

All figures, tables, and conclusions should be reproducible.
`RiddlesBenchmarking/analysis` will be used to improve publication transparency.
To contribute an analysis, create a new analysis notebook/script for the dataset
version you are examining. It will be important to use the same colors and fonts
for the figure. The final style may vary based on the publication venues chosen
later, but use `style.py` in your analysis now so that we will simply need to
rerun your analysis later after finalizing the look and feel of a publication
for a given manuscript. Every figure draws its colors and fonts from one shared
style file (`style.py`) to ensure visual consistency.

It only *reads* the sibling packages' outputs (the dataset in `data_loading/`, runs
in `framework/runs/`, scores in `evals/outputs/`). Everything it writes — generated
figures — lands in `analysis/figures/`.


Currently, this package turns the benchmark's artifacts — the V0 dataset and a
run's `results.jsonl` — into the figures and tables used for publication. As
additional datasets and evals become available from other teams these will also
be examined here.


## Setup

```bash
python -m pip install -r requirements.txt
```

Pulls in matplotlib, seaborn, and pandas. `matplotlib >= 3.6` is required for the
per-glyph font fallback the style relies on (see "Fonts" below).

## The shared style

`style.py` is the single source of truth for how figures look. Call it once at the
top of any script or notebook, then pull colors from the named palette — never
hard-code a hex value in a plot:

```python
from analysis.style import apply_style, save_figure, PALETTE, CONDITION_COLORS

apply_style()                         # serif "LaTeX-paper" look + colorblind-safe palette
...                                    # build your figure, coloring from PALETTE / CONDITION_COLORS
save_figure(fig, "analysis/figures/my_figure")   # 300 dpi vector PDF, fonts embedded
```

- **Colors** are the Okabe–Ito colorblind-safe set; `CONDITION_COLORS` maps the three
  benchmark conditions to fixed colors so they read the same across every figure.
- **Fonts** use a serif stack (STIX Two Text, bundled with matplotlib) with Computer
  Modern math, for a LaTeX look *without* the fragility of `text.usetex`. The benchmark
  spans many writing systems, so the stack falls back per glyph to broader fonts. For
  fully reproducible non-Latin rendering, vendor the open-licensed Noto fonts into
  `analysis/fonts/` and call `register_fonts()` before `apply_style()`.

## Quick start

For a worked example see the notebook
[`V0DataV0Analysis.ipynb`](V0DataV0Analysis.ipynb), which loads the V0 dataset,
examines which "wildcard" topics communities choose, and renders the answer
using the shared style.

## Layout

```
analysis/
├── style.py                       # shared color scheme + fonts (apply_style, PALETTE, save_figure)
├── V0DataV0Analysis.ipynb         # notebook template: wildcard topics across cultures
├── requirements.txt
└── figures/                       # generated output (PDF)
```
