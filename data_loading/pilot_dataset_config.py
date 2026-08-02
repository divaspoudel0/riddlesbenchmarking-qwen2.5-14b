"""Configuration for building the pilot dataset.

Centralizes lookups and mappings so they can be edited without touching
the build logic. Add new languages, schema fields, or topic rules here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Language codes
# ---------------------------------------------------------------------------
# Maps community language token (lowercased, derived from filename) to
# ISO 639-2/639-3 code. Verified by inspecting actual riddle source content
# where dialects were ambiguous (Arabic varieties, Cantonese, Mongondow).
#
# Notes:
#   - Arabic dialects use 639-3 codes (arz, apd, apc, ary) since 639-2
#     only has the macro-language "ara". This is the standard practice for
#     dialect-specific benchmarks.
#   - "mog" (Mongondow) only exists in 639-3.
#   - "yue" (Cantonese) is 639-3; sits inside the 639-2 macro-language "chi".

LANGUAGE_TO_ISO_639_2 = {
    # ----- Compound keys (community-specific dialect codes) -----
    # When a language has dialects that vary by country, we use the full
    # community key so the right ISO 639-3 dialect code is selected.
    "arabic_egypt": "arz",         # Egyptian Arabic
    "arabic_morocco": "ary",       # Moroccan Arabic / Darija
    "arabic_sudan": "apd",         # Sudanese Arabic (NOT Sundanese)
    "arabic_syria": "apc",         # North Levantine Arabic
    "arabic_lebanese": "apc",      # Lebanese = North Levantine Arabic (same code as Syria)
    "afaan_oromo_oromo": "gaz",    # Afaan Oromo = West Central Oromo (standard written form)

    # ----- Simple keys (first-token lookup) -----
    "assamese": "asm",            # Assamese (Bengali-Assamese script)
    "belarusian": "bel",
    "bengali": "ben",
    "brazilian": "por",            # Brazilian Portuguese (no separate 639-3 code)
    "bugisnese": "bug",
    "bulgarian": "bul",
    "cantonese": "yue",            # verified by source inspection
    "catalan": "cat",
    "chinese": "zho",
    "dutch": "nld",
    "egyptian": "arz",             # legacy alias; new filenames use arabic_egypt
    "english": "eng",
    "french": "fra",
    "german": "deu",
    "gujarati": "guj",             # script detector returns "unknown" for Gujarati (skipped, no false warning)
    "hungarian": "hun",
    "indonesian": "ind",
    "italian": "ita",
    "japanese": "jpn",
    "kannada": "kan",
    "konkani": "kok",
    "luganda": "lug",
    "lumasaba": "myx",             # Lumasaba (Bukusu/Bagisu)
    "lusoga": "xog",
    "luxembourgish": "ltz",
    "malay": "zsm",                # Standard Malay
    "malayalam": "mal",
    "marathi": "mar",
    "mongondow": "mog",            # Bolaang Mongondow, verified
    "moroccan": "ary",             # legacy alias; new filenames use arabic_morocco
    "nepali": "nep",
    "persian": "pes",              # Iranian Persian (Western Farsi)
    "polish": "pol",
    "portuguese": "por",
    "runyankole": "nyn",           # alt spelling of runyankore
    "runyankore": "nyn",
    "russian": "rus",
    "serbian": "srp",
    "sindhi": "snd",               # Sindhi (India community uses Perso-Arabic script)
    "sinhala": "sin",
    "spanish": "spa",
    "sudanese": "apd",             # legacy alias; new filenames use arabic_sudan
    "swahili": "swa",
    "syrian": "apc",               # legacy alias; new filenames use arabic_syria
    "tamil": "tam",
    "telugu": "tel",
    "thai": "tha",
    "tunisian": "aeb",           # Tunisian Arabic (639-3); first-token key is unambiguous
    "turkish": "tur",
    "ukrainian": "ukr",
    "urdu": "urd",
    "uzbek": "uzb",
    "vietnamese": "vie",
    "yoruba": "yor",
}

# Expected Unicode script family for each ISO code. Used by the script-
# detection sanity check (Option A) to catch mismatches between the
# mapping and actual riddle content. Languages not listed default to
# "latin".
ISO_TO_SCRIPT_FAMILY = {
    # Arabic-script
    "arz": "arabic",
    "apd": "arabic",
    "apc": "arabic",
    "ary": "arabic",
    "aeb": "arabic",
    "urd": "arabic",
    "snd": "arabic",              # Sindhi (India) in Perso-Arabic script
    # Han (Chinese characters)
    "yue": "han",
    "zho": "han",
    "jpn": "han",                 # kanji detected as han; kana-only rows read "unknown" (skipped)
    # Cyrillic
    "bel": "cyrillic",
    "bul": "cyrillic",
    "rus": "cyrillic",
    "srp": "cyrillic",
    "ukr": "cyrillic",
    # Brahmic family — each Indic script gets its own family
    "asm": "bengali",             # Assamese shares the Bengali Unicode block
    "ben": "bengali",
    "hin": "devanagari",
    "kan": "kannada",
    "mal": "malayalam",
    "mar": "devanagari",
    "nep": "devanagari",
    "tam": "tamil",
    "tel": "telugu",
    # Thai
    "tha": "thai",
    # Iranian Persian (Western Farsi) uses Arabic script
    "pes": "arabic",
    # Konkani primarily uses Devanagari (also Kannada/Roman in some regions)
    "kok": "devanagari",
    # Sinhala has its own Unicode block; script detector returns "unknown"
    # for it, so we skip the explicit mapping (no false warnings)
    # Yoruba uses Latin script with diacritics — covered by DEFAULT_SCRIPT_FAMILY
    # Vietnamese uses Latin script with diacritics — covered by DEFAULT_SCRIPT_FAMILY
    # Latin-script (everything else defaults to this)
}

DEFAULT_SCRIPT_FAMILY = "latin"


# ---------------------------------------------------------------------------
# Schema mapping
# ---------------------------------------------------------------------------
# Maps template column names (what contributors fill in) to canonical
# schema field names (what the Analysis team consumes). Source columns
# not listed here are preserved under the nested `raw_template_fields`
# object in v1 and reviewed before being dropped or added to canonical
# in v2.

TEMPLATE_TO_CANONICAL = {
    "Number": "source_row_number",
    "Topic": "topic",
    "Author": "author_credit",
    "Riddle (Original Language)": "riddle_original",
    "Riddle (English Translation)": "riddle_english",
    "English Translation": "riddle_english",      # variant some files use
    "Hints (Optional)": "riddle_hint",
    "Comments (Optional), e.g. about region/generation-specificity": "riddle_note",
    "Reference Answer (Original)": "reference_answer_original",
    "Reference Answer (English)": "reference_answer_english",
    "Human Validator Name": "human_validator_name",
    "Human Answer (Original)": "human_answer_original",
    "Rating of Human Answer (0-2)": "human_answer_score",
    "Comment (Optional) about evaluation of human answer": "human_answer_comment",
}

# Order of fields in the output JSONL. Anything not listed appears at
# the end in insertion order. Keep canonical schema fields first.
SCHEMA_FIELD_ORDER = [
    "instance_result_id",
    "riddle_id",
    "created_at",
    "source_row_number",
    "language",
    "community",
    "run_batch",
    "topic",
    "is_wildcard",
    "riddle_original",
    "riddle_english",
    "reference_answer_original",
    "reference_answer_english",
    "riddle_hint",
    "riddle_note",
    "author_credit",
    "human_validator_name",
    "human_answer_original",
    "human_answer_score",
    "human_answer_comment",
    "row_status",
    "raw_template_fields",
]


# ---------------------------------------------------------------------------
# Topic rules
# ---------------------------------------------------------------------------
# The 8 standard topics every community must cover. Anything else is
# treated as a wildcard (community-specific choice).

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
