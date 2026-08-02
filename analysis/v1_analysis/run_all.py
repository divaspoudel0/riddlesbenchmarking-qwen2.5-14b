from __future__ import annotations

import argparse
from pathlib import Path

import answer_diversity_analysis
import form_length_analysis
import lexical_diversity_analysis
import load_data
import summary_table
import validator_analysis
import wildcard_analysis
from text_features import CSV_DIR, FIGURES_DIR

DEFAULT_INPUT_DIR = Path.home() / "Downloads" / "v1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    args = parser.parse_args()

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    consolidated, quality_df = load_data.build_consolidated_dataset(args.input_dir, CSV_DIR)
    consolidated.to_csv(CSV_DIR / "riddles_v1_consolidated.csv", index=False)
    quality_df.to_csv(CSV_DIR / "data_quality_notes.csv", index=False)

    wildcard_analysis.main()
    form_length_analysis.main()
    answer_diversity_analysis.main()
    lexical_diversity_analysis.main()
    validator_analysis.main()
    summary_table.main()


if __name__ == "__main__":
    main()
