import pandas as pd
import numpy as np
from pathlib import Path
import logging
import re

# define logging config
logging.basicConfig(
    filename="null_values.log",
    encoding="utf-8",
    filemode="a",
    level=logging.ERROR
)

other_notes_logger = logging.getLogger("other_notes")
other_notes_logger.setLevel(logging.ERROR)

other_notes_handler = logging.FileHandler("other_notes.log", encoding="utf-8", mode="a")

other_notes_logger.addHandler(other_notes_handler)
other_notes_logger.propagate = False

NAME_PATTERN = re.compile(r"^Human Eval (?P<language>\w+)_(?P<country>\w+)$", re.IGNORECASE)
REQUIRED_COLUMNS = ["Annotator Name", "Score (0-3)", "Error Type"]
OTHER_ERROR_VALUE = ["0.4 - Other (add note)", "2.4 - Other (add note)"]
# 1. First read .csv files.
# I assumed that the data are located in `HumanEval` folder 
# relative path: humaneval_validation\HumanEval
def load_files(input_path):
    try:
        folder = Path(input_path)
        dfs = []
        skipped = []

        for f in folder.glob("*.xlsx"):
            match = NAME_PATTERN.match(f.stem)
            if not match:
                skipped.append(f.name)
                continue

            language = match.group("language")
            country = match.group("country")

            sheets = pd.read_excel(f, sheet_name=None)  # dict of {sheet_name: df}
            dfs.append({
                "language": language,
                "country": country,
                "sheets": sheets,
            })
        print(f"Loaded {len(dfs)} matching files")
        if skipped:
            print(f"Skipped {len(skipped)} non-matching files: {skipped}")

        return dfs
    except Exception as e:
        logging.error(f"error while finding the files: {e}")



# 2.1. Check that ["Annotator Name", "Score (0-3)", "Error Type"] don't include any null value for the main sheet
def check_nulls_sheet1(dfs):
    issues = []

    for entry in dfs:
        language = entry["language"]
        country = entry["country"]
        sheets = entry["sheets"]
        sheet_name = next(iter(sheets))
        df = sheets[sheet_name]
        tag = f"{language}_{country}"

        logging.error("-" * 80)
        logging.error(f"Checking {tag} / {sheet_name} Main")

        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                issues.append({
                    "language": language, "country": country,
                    "sheet": sheet_name, "column": col,
                    "problem": "column missing", "row_count": None,
                })
                logging.error(f"[{tag} / {sheet_name}] Missing column: '{col}'")
                continue

            null_mask = df[col].isnull()
            null_count = null_mask.sum()
            if null_count > 0:
                row_indices = df.index[null_mask].tolist()
                issues.append({
                    "language": language, "country": country,
                    "sheet": sheet_name, "column": col,
                    "problem": "null values", "row_count": int(null_count),
                    "row_indices": row_indices,
                })
                logging.error(f"[{tag} / {sheet_name}] '{col}' has {null_count} null(s) at rows {row_indices}")

    if not issues:
        print("[sheet 1] No issues found.")
    return issues


# 2.2. Check that ["Annotator Name", "Score (0-3)", "Error Type"] don't include any null value for the extra sheet
def check_nulls_sheet2(dfs):
    issues = []

    for entry in dfs:
        language = entry["language"]
        country = entry["country"]
        sheets = entry["sheets"]
        sheet_names = list(sheets)
        tag = f"{language}_{country}"
        # check that Extra sheet exists
        if len(sheet_names) < 2:
            issues.append({
                "language": language, "country": country,
                "sheet": None, "column": None,
                "problem": "second sheet missing", "row_count": None,
            })
            continue

        sheet_name = sheet_names[1]  # second tab
        df = sheets[sheet_name]
        logging.error("-" * 80)
        logging.error(f"Checking {language}_{country} / {sheet_name}")
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                issues.append({
                    "language": language, "country": country,
                    "sheet": sheet_name, "column": col,
                    "problem": "column missing", "row_count": None,
                })
                logging.error(f"[{tag} / {sheet_name}] Missing column: '{col}'")
                continue

            null_mask = df[col].isnull()
            null_count = null_mask.sum()
            if null_count > 0:
                row_indices = df.index[null_mask].tolist()
                issues.append({
                    "language": language, "country": country,
                    "sheet": sheet_name, "column": col,
                    "problem": "null values", "row_count": int(null_count),
                    "row_indices": df.index[null_mask].tolist(),
                })
                logging.error(f"[{tag} / {sheet_name}] '{col}' has {null_count} null(s) at rows {row_indices}")

    if not issues:
        print("[sheet 2] No issues found.")
    return issues



# 3. Check that the Validator Note exists for rows in which have Other (add note) as Error Type.
def check_other_notes(dfs, sheet_index=0):
    """
    sheet_index=0 -> main sheet, sheet_index=1 -> extra sheet.
    """
    issues = []

    for entry in dfs:
        language = entry["language"]
        country = entry["country"]
        sheets = entry["sheets"]
        sheet_names = list(sheets)
        tag = f"{language}_{country}"
        # print(f"checking: {tag}")
        if len(sheet_names) <= sheet_index:
            issues.append({
                "language": language, "country": country,
                "sheet": None, "column": "Validator Note",
                "problem": f"sheet index {sheet_index} missing", "row_count": None,
            })
            continue

        sheet_name = sheet_names[sheet_index]
        df = sheets[sheet_name]

        if "Error Type" not in df.columns:
            issues.append({
                "language": language, "country": country,
                "sheet": sheet_name, "column": "Error Type",
                "problem": "column missing", "row_count": None,
            })
            continue

        if "Validator Note" not in df.columns:
            issues.append({
                "language": language, "country": country,
                "sheet": sheet_name, "column": "Validator Note",
                "problem": "column missing", "row_count": None,
            })
            continue

        other_mask = df["Error Type"].isin(OTHER_ERROR_VALUE) 

        # print(df["Error Type"].value_counts())
        # print(df["Validator Note"].value_counts())

        empty_note_mask = df["Validator Note"].isnull() | (df["Validator Note"].astype(str).str.strip() == "")
        bad_mask = other_mask & empty_note_mask

        bad_count = bad_mask.sum()
        if bad_count > 0:
            row_indices = df.index[bad_mask].tolist()
            issues.append({
                "language": language, "country": country,
                "sheet": sheet_name, "column": "Validator Note",
                "problem": "missing note for 'Other' error type",
                "row_count": int(bad_count),
                "row_indices": row_indices,
            })
            other_notes_logger.error(
                f"[{tag} / {sheet_name}] {bad_count} row(s) with Error Type='{OTHER_ERROR_VALUE}' "
                f"but empty Validator Note at rows {row_indices}"
            )
            # print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    if not issues:
        print(f"[Other-note check, sheet_index={sheet_index}] No issues found.")
    return issues


if __name__ == "__main__":
    base_dir = Path(__file__).parent
    data_folder_path = base_dir / "HumanEval"
    data = load_files(data_folder_path)
    # check for the main sheet
    # issues1 = check_nulls_sheet1(data)
    # check extra
    # issues2 = check_nulls_sheet2(data)

    # check for the main sheet
    other_issues1 = check_other_notes(data, sheet_index=0)

    # check for the extra
    other_issues2 = check_other_notes(data, sheet_index=1)



