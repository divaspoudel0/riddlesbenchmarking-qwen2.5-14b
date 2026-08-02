from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd
from wordfreq import zipf_frequency

STANDARD_TOPICS = {
    "Politics",
    "History",
    "Geography",
    "Arts",
    "Sports",
    "National Heritage",
    "Kid's World",
    "Everyday Life",
}

COLUMN_ALIASES = {
    "Number": "source_row_number",
    "Topic": "topic",
    "Author": "author_credit",
    "Riddle (Original Language)": "riddle_original",
    "Riddle (English Translation)": "riddle_english",
    "English Translation": "riddle_english",
    "Hints (Optional)": "riddle_hint",
    "Comments (Optional), e.g. about region/generation-specificity": "riddle_note",
    "Comments (Optional), e.g. about region/generation specificity": "riddle_note",
    "Comments (Optional)": "riddle_note",
    "Reference Answer (Original)": "reference_answer_original",
    "Reference Answer (English)": "reference_answer_english",
    "Human Validator Name": "human_validator_name",
    "Human Answer (Original)": "human_answer_original",
    "Human Validator Answer (Original)": "human_answer_original",
    "Rating of Human Answer (0-2)": "human_answer_score",
    "Rating of human answer (0-2)": "human_answer_score",
    "Rating of Human Answer (0 2)": "human_answer_score",
    "Rating of Human Answer (0-3)": "human_answer_score",
    "Comment (Optional) about evaluation of human answer": "human_answer_comment",
    "Comment (Optional)": "human_answer_comment",
}

CANONICAL_COLUMNS = [
    "source_row_number",
    "topic",
    "author_credit",
    "riddle_original",
    "riddle_english",
    "riddle_hint",
    "riddle_note",
    "reference_answer_original",
    "reference_answer_english",
    "human_validator_name",
    "human_answer_original",
    "human_answer_score",
    "human_answer_comment",
]

FILENAME_PATTERN = re.compile(r"\[(.+)\]")
WILDCARD_LABEL_RE = re.compile(r"Wildcard\s*\d*\s*\[(.+)\]", re.IGNORECASE)
WORD_SPLIT_RE = re.compile(r"\S+")
TOKEN_RE = re.compile(r"[A-Za-z']+")
FIRST_PERSON_RE = re.compile(r"\b(i|i'm|i've|i'll|i'd|my|me|myself)\b", re.IGNORECASE)

def find_repo_root(start: Path) -> Path:
    for folder in [start, *start.parents]:
        if (folder / "analysis" / "style.py").exists():
            return folder
    raise FileNotFoundError(f"Could not find analysis/style.py above {start}")


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)
CSV_DIR = Path(__file__).resolve().parent / "csv"
FIGURES_DIR = Path(__file__).resolve().parent / "figures"

ENTITY_LIKE_MAX_WORDS = 3
RARE_ZIPF_THRESHOLD = 3.0
MIN_RATINGS_FOR_OUTCOME_CHART = 5
LOW_FILL_EXCLUSION_THRESHOLD = 50
DUPLICATE_OVERLAP_THRESHOLD = 0.9
NEAR_DUPLICATE_OVERLAP_THRESHOLD = 0.15


def community_token_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    match = FILENAME_PATTERN.search(stem)
    inner = match.group(1) if match else stem
    inner = "".join(ch for ch in inner if unicodedata.category(ch) not in {"So", "Cs"})
    inner = re.sub(r"\s+", " ", inner).strip()
    return inner


def display_label(community: str) -> str:
    language, _, country = community.partition("_")
    if country:
        return f"{language}, {country}"
    return community


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {c: COLUMN_ALIASES[c] for c in df.columns if c in COLUMN_ALIASES}
    renamed = df.rename(columns=rename_map)
    for col in CANONICAL_COLUMNS:
        if col not in renamed.columns:
            renamed[col] = pd.NA
    return renamed[CANONICAL_COLUMNS].copy()


def strip_phantom_rows(df: pd.DataFrame) -> pd.DataFrame:
    if "riddle_original" not in df.columns:
        return df
    return df.loc[df["riddle_original"].notna()].reset_index(drop=True)


def clean_topic_label(topic: object) -> object:
    if pd.isna(topic):
        return topic
    text = str(topic).strip()
    match = WILDCARD_LABEL_RE.match(text)
    return match.group(1).strip() if match else text


def is_wildcard_topic(topic: object) -> bool:
    if pd.isna(topic):
        return False
    return str(topic).strip() not in STANDARD_TOPICS


def word_count(text: object) -> int:
    if pd.isna(text):
        return 0
    return len(WORD_SPLIT_RE.findall(str(text)))


def is_question(text: object) -> bool:
    if pd.isna(text):
        return False
    return str(text).strip().endswith("?")


def is_first_person(text: object) -> bool:
    if pd.isna(text):
        return False
    return bool(FIRST_PERSON_RE.search(str(text)))


def is_multiline(text: object) -> bool:
    if pd.isna(text):
        return False
    return "\n" in str(text).strip()


def entity_like_answer(text: object, max_words: int = ENTITY_LIKE_MAX_WORDS) -> bool:
    if pd.isna(text):
        return False
    return word_count(text) <= max_words


def normalize_answer_text(text: object) -> object:
    if pd.isna(text):
        return pd.NA
    return " ".join(str(text).strip().casefold().split())


def tokenize_english(text: object) -> list[str]:
    if pd.isna(text):
        return []
    return [tok.lower() for tok in TOKEN_RE.findall(str(text))]


def zipf(word: str) -> float:
    return zipf_frequency(word, "en")


def is_rare_token(word: str, threshold: float = RARE_ZIPF_THRESHOLD) -> bool:
    return zipf(word) < threshold


def reconcile_score_label(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    text = str(value).strip()
    low = text.lower()
    if low.startswith("rating of"):
        return pd.NA
    if "partial" in low or "somewhat" in low:
        return "partial"
    if "wrong" in low or "incorrect" in low or "hallucinat" in low:
        return "incorrect"
    if "don't know" in low or "dont know" in low or "uncertain" in low:
        return "uncertain"
    if "correct" in low:
        return "correct"
    try:
        numeric = int(float(text))
    except ValueError:
        return pd.NA
    return {0: "incorrect", 1: "partial", 2: "correct", 3: "correct"}.get(numeric, pd.NA)


THEME_KEYWORDS = {
    "Food & Gastronomy": ["food", "cuisine", "culinary", "cook", "coook", "dish", "gastronom", "gasronom"],
    "Nature & Environment": ["nature", "environment", "agricultur"],
    "Animals": ["animal", "wildlife", "insect"],
    "Plants": ["plant"],
    "Anatomy & Body": ["anatomy", "body"],
    "Cinema, TV & Pop Culture": ["cinema", "movie", "film", "hollywood", "tv", "popcultur", "pop cultur"],
    "Music": ["music", "instrument", "song"],
    "Language, Proverbs & Sayings": [
        "proverb", "saying", "idiom", "dialect", "express", "slang", "pun", "colloquial", "language",
    ],
    "Religion, Myth & Folklore": ["religio", "myth", "legend", "folklore", "belief", "spiritual"],
    "Festivals & Celebrations": ["festival", "celebrat", "ritual"],
    "Economy & Work": ["econom", "work life", "career"],
    "Science & Technology": ["scien", "technolog"],
    "Literature": ["literat"],
    "Clothing & Objects": ["cloth", "object", "thing"],
    "Society & Identity": ["cultur", "humanit", "caste", "relationship", "gen-z", "genz"],
    "Places & Travel": ["travel", "map", "moscow"],
}

THEME_PATTERNS = {
    theme: [re.compile(r"\b" + re.escape(keyword), re.IGNORECASE) for keyword in keywords]
    for theme, keywords in THEME_KEYWORDS.items()
}


def themes_for_topic_label(label: object) -> list[str]:
    if pd.isna(label):
        return []
    text = str(label)
    matched = []
    for theme, patterns in THEME_PATTERNS.items():
        if any(pattern.search(text) for pattern in patterns):
            matched.append(theme)
    return matched


def jaccard_overlap(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    smaller = min(len(set_a), len(set_b))
    return intersection / smaller if smaller else 0.0
