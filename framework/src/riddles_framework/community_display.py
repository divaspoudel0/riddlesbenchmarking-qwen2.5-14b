"""Human-readable display names for community keys.

Community keys in the pilot dataset use the form "language_country" (e.g.
"tamil_india", "arabic_morocco"). These keys are great for grouping and
joins but read poorly inside a prompt sent to an LLM.

This module maps each community key to a human-readable form, e.g.
    "arabic_morocco" -> "Moroccan Arabic, Morocco"
    "tamil_india"    -> "Tamil, India"

When a key is missing from the table, format_community_display() falls
back to titlecasing the parts (e.g. "konkani_india" -> "Konkani, India")
so new communities still render reasonably without a code change.

If the team's master prompt design ever needs a different rendering style
(e.g. just the language name, or "[Language] from [Country]"), update
format_community_display() rather than maintaining parallel mappings
everywhere.
"""

from __future__ import annotations


# Curated, hand-checked display names for known communities.
# When you add a new community, prefer an entry here over relying on the
# auto-titlecase fallback, especially for Arabic varieties and other
# cases where the natural English rendering isn't a straight titlecase.
COMMUNITY_DISPLAY: dict[str, str] = {
    # Arabic varieties
    "arabic_egypt": "Egyptian Arabic, Egypt",
    "arabic_morocco": "Moroccan Arabic, Morocco",
    "arabic_sudan": "Sudanese Arabic, Sudan",
    "arabic_syria": "Syrian Arabic, Syria",
    # Asia
    "belarusian_belarus": "Belarusian, Belarus",
    "bengali_bangladesh": "Bengali, Bangladesh",
    "bengali_india": "Bengali, India",
    "bugisnese_indonesia": "Buginese, Indonesia",
    "bulgarian_bulgaria": "Bulgarian, Bulgaria",
    "cantonese_china": "Cantonese, China",
    "chinese_china": "Mandarin Chinese, China",
    "chinese_simplified_china": "Mandarin Chinese (Simplified), China",
    "dutch_netherlands": "Dutch, Netherlands",
    "english_canada": "English, Canada",
    "english_usa": "English, United States",
    "french_france": "French, France",
    "german_germany": "German, Germany",
    "hungarian_hungary": "Hungarian, Hungary",
    "indonesian_indonesia": "Indonesian, Indonesia",
    "italian_italy": "Italian, Italy",
    "kannada_india": "Kannada, India",
    "konkani_india": "Konkani, India",
    "luganda_uganda": "Luganda, Uganda",
    "lumasaba_uganda": "Lumasaba, Uganda",
    "lusoga_uganda": "Lusoga, Uganda",
    "malayalam_india": "Malayalam, India",
    "marathi_india": "Marathi, India",
    "mongondow_indonesia": "Mongondow, Indonesia",
    "nepali_nepal": "Nepali, Nepal",
    "persian_iran": "Persian, Iran",
    "polish_poland": "Polish, Poland",
    "portuguese_portugal": "Portuguese, Portugal",
    "runyankole_uganda": "Runyankole, Uganda",
    "russian_russia": "Russian, Russia",
    "serbian_serbia": "Serbian, Serbia",
    "sinhala_sri_lanka": "Sinhala, Sri Lanka",
    "spanish_argentina": "Spanish, Argentina",
    "spanish_cuba": "Spanish, Cuba",
    "spanish_peru": "Spanish, Peru",
    "swahili_kenya": "Swahili, Kenya",
    "tamil_india": "Tamil, India",
    "telugu_india": "Telugu, India",
    "thai_thailand": "Thai, Thailand",
    "urdu_pakistan": "Urdu, Pakistan",
    "uzbek_uzbekistan": "Uzbek, Uzbekistan",
    "yoruba_nigeria": "Yoruba, Nigeria",
}


def format_community_display(community: str) -> str:
    """Render a community key as a human-readable name.

    Looks up the curated mapping first. Falls back to a titlecased
    "Language, Country" rendering so new communities still render
    sensibly without requiring a code change.
    """
    if not community:
        return "(unspecified)"

    key = community.strip().lower()
    if key in COMMUNITY_DISPLAY:
        return COMMUNITY_DISPLAY[key]

    # Fallback: titlecase parts. "konkani_india" -> "Konkani, India".
    parts = key.split("_", 1)
    if len(parts) == 2:
        language, country = parts
        return f"{language.title()}, {country.replace('_', ' ').title()}"
    return key.title()


def format_country(community: str) -> str:
    """Extract just the country portion of a community key, titlecased.

    "tamil_india" -> "India"
    "arabic_morocco" -> "Morocco"
    """
    if not community:
        return "(unspecified)"
    parts = community.strip().lower().split("_", 1)
    if len(parts) == 2:
        return parts[1].replace("_", " ").title()
    return "(unspecified)"


def format_language_name(community: str) -> str:
    """Extract just the language portion of a community key, titlecased.

    Useful when the template wants the language as a word rather than
    an ISO code. "tamil_india" -> "Tamil".
    """
    if not community:
        return "(unspecified)"
    parts = community.strip().lower().split("_", 1)
    if not parts:
        return "(unspecified)"
    return parts[0].title()


# ---------------------------------------------------------------------------
# Script handling (ISO 15924)
# ---------------------------------------------------------------------------
#
# Maps a community key to its primary writing script's ISO 15924 code.
# This is a v1 simplification: one script per community.
#
# Why script matters in the prompt:
#   - Several languages can be written in multiple scripts (Konkani in
#     Devanagari/Kannada/Roman, Arabic dialects in Arab/Latn for informal
#     use, Serbian in Cyrl/Latn). Without an explicit signal, the model
#     may render its answer in the "wrong" script for the dataset.
#   - The Moroccan Arabic case (flagged by Abdellah): "arabic_morocco"
#     written in Arabic script vs. Latin script (Darija romanization)
#     are visually and orthographically very different. Telling the model
#     "written in Arabic script" disambiguates this cleanly.
#
# Future work: when the data_loading pipeline adds a per-workbook `script`
# field to the dataset schema, the framework should prefer that over
# this community-level default. This mapping then becomes a fallback for
# rows without an explicit script declaration.
COMMUNITY_TO_SCRIPT_ISO: dict[str, str] = {
    # Arabic varieties — all use Arabic script in their canonical form
    "arabic_egypt": "Arab",
    "arabic_morocco": "Arab",
    "arabic_sudan": "Arab",
    "arabic_syria": "Arab",
    # South Asian scripts
    "bengali_bangladesh": "Beng",
    "bengali_india": "Beng",
    "kannada_india": "Knda",
    "konkani_india": "Deva",        # primarily Devanagari (also written in Kannada/Roman)
    "malayalam_india": "Mlym",
    "marathi_india": "Deva",
    "nepali_nepal": "Deva",
    "sinhala_sri_lanka": "Sinh",
    "tamil_india": "Taml",
    "telugu_india": "Telu",
    "urdu_pakistan": "Arab",        # Urdu uses Perso-Arabic script
    # East / Southeast Asia
    "cantonese_china": "Hant",      # Traditional Han (HK/Macau)
    "chinese_china": "Hans",        # Simplified Han (mainland)
    "chinese_simplified_china": "Hans",  # Explicitly Simplified Han
    "thai_thailand": "Thai",
    # Persian
    "persian_iran": "Arab",         # Persian alphabet, Arabic script family
    # Cyrillic-using languages
    "belarusian_belarus": "Cyrl",
    "bulgarian_bulgaria": "Cyrl",
    "russian_russia": "Cyrl",
    "serbian_serbia": "Cyrl",        # Serbian uses Cyrillic in Serbia (Latin also used)
    # Latin-script languages (explicit so the prompt is informative)
    "brazilian_portuguese": "Latn",
    "bugisnese_indonesia": "Latn",  # contemporary Buginese; Lontara script is rare in modern usage
    "dutch_netherlands": "Latn",
    "english_canada": "Latn",
    "english_usa": "Latn",
    "french_france": "Latn",
    "german_germany": "Latn",
    "hungarian_hungary": "Latn",
    "indonesian_indonesia": "Latn",
    "italian_italy": "Latn",
    "luganda_uganda": "Latn",
    "lumasaba_uganda": "Latn",
    "lusoga_uganda": "Latn",
    "mongondow_indonesia": "Latn",
    "polish_poland": "Latn",
    "portuguese_portugal": "Latn",
    "runyankole_uganda": "Latn",
    "spanish_argentina": "Latn",
    "spanish_cuba": "Latn",
    "spanish_peru": "Latn",
    "swahili_kenya": "Latn",
    "uzbek_uzbekistan": "Latn",    # current official script in Uzbekistan (Cyrl also exists)
    "yoruba_nigeria": "Latn",
}

# Human-readable script names indexed by ISO 15924 code.
SCRIPT_ISO_TO_NAME: dict[str, str] = {
    "Arab": "Arabic script",
    "Beng": "Bengali script",
    "Cyrl": "Cyrillic script",
    "Deva": "Devanagari script",
    "Hans": "Simplified Chinese script",
    "Hant": "Traditional Chinese script",
    "Knda": "Kannada script",
    "Latn": "Latin script",
    "Mlym": "Malayalam script",
    "Sinh": "Sinhala script",
    "Taml": "Tamil script",
    "Telu": "Telugu script",
    "Thai": "Thai script",
}


def format_script_iso(community: str) -> str:
    """Return the ISO 15924 code for the community's primary script.

    Falls back to empty string if the community is unknown, so a
    template author can spot the gap (the {script_iso} placeholder
    renders as empty rather than fabricating a code).
    """
    if not community:
        return ""
    return COMMUNITY_TO_SCRIPT_ISO.get(community.strip().lower(), "")


def format_script_name(community: str) -> str:
    """Return a human-readable script name for use in prompts.

    Examples:
        "arabic_morocco" -> "Arabic script"
        "tamil_india"    -> "Tamil script"
        "english_usa"    -> "Latin script"

    Unknown communities return "(unspecified)" so templates render
    sensibly rather than producing empty fragments like "written in .".
    """
    iso = format_script_iso(community)
    if not iso:
        return "(unspecified)"
    return SCRIPT_ISO_TO_NAME.get(iso, iso)
