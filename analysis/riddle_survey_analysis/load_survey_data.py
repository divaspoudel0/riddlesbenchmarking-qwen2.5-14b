from text_features import CSV_DIR, FIGURES_DIR, REPO_ROOT
import pandas as pd
import numpy as np


DIFF_COLS=[
    "diff_politics", "diff_history", "diff_geography", "diff_arts", "diff_sports",
    "diff_national_heritage", "diff_kids_world", "diff_everyday_life", "diff_wildcard_1&2"
]

DIFF_LABELS= [
    "Politics", "History", "Geography", "Arts", "Sports",
    "Nat.\nHeritage", "Kid's\nWorld", "Everyday\nLife", "Wild\nCard",

]

def load_survey_data():
    path= CSV_DIR/"[MCB]_Analysis_MasterSheet - reflection_form.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")

    survey_data= pd.read_csv(path)
    cols= survey_data.columns.tolist()

    survey_data= survey_data.rename(columns={
        cols[1]: "community",
        cols[4]: "confidence",
        cols[5]: "confidence_why",
        cols[6]: "topics_selected",
        cols[7]: "translate_ease",
        cols[8]: "lost_in_translation",
        cols[9]: "time_per_riddle",
        cols[10]: "difficulty_overall",
        cols[11]: "diff_politics",
        cols[12]: "diff_history",
        cols[13]: "diff_geography",
        cols[14]: "diff_arts",
        cols[15]: "diff_sports",
        cols[16]: "diff_national_heritage",
        cols[17]: "diff_kids_world",
        cols[18]: "diff_everyday_life",
        cols[19]: "diff_wildcard_1&2",
        cols[20]: "resources_used",
        cols[21]: "resources_howused",
        cols[22]: "local_specificity",
        cols[23]: "culture_features",
        cols[24]: "wildcard_choice",
        cols[25]: "process_reflection",
        cols[26]: "instructions_clarity",
        cols[27]: "project_feedback",
        cols[28]: "survey_feedback"
    })

    for c in DIFF_COLS:
        survey_data[c]= pd.to_numeric(
            survey_data[c].replace("0 - N/A", np.nan), errors="coerce"
        )

    for c in ["confidence", "translate_ease", "difficulty_overall",
              "instructions_clarity"]:
        survey_data[c]= pd.to_numeric(survey_data[c], errors="coerce")


    return survey_data




