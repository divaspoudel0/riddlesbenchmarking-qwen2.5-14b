from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path
import numpy as np
from text_features import REPO_ROOT, FIGURES_DIR
from load_survey_data import load_survey_data

sys.path.insert(0, str(REPO_ROOT))

from analysis.style import PALETTE, CONDITION_COLORS, apply_style, save_figure
import matplotlib.pyplot as plt

df = load_survey_data()

KNOWN_MULTIWORD = [
    "Books, articles, websites, or other reference materials (e.g., museum artifacts)",
    "Online encyclopedia/General search (e.g., Wikipedia, Google)",

]


def split_multiselect(value: str, known: list[str] = KNOWN_MULTIWORD):
    """Split comma seperated multi select cell without breaking known multi-word
    options that themselves contain commas"""

    s = str(value)
    placeholders: dict[str, str] = {}
    for i, phrase in enumerate(known):
        if phrase in s:
            ph = f"__PH{i}__"
            placeholders[ph] = phrase
            s = s.replace(phrase, ph)

    parts = [x.strip() for x in s.split(',')]
    out: list[str] = []

    for part in parts:
        for ph, phrase in placeholders.items():
            part = part.replace(ph, phrase)
        if part.strip():
            out.append(part.strip())

    return out


def calculate_used_resources():
    """ used for tallying the resources used by the respondents"""

    fixed = [
        "Personal knowledge/Experience",
        "Online encyclopedia/General search (e.g., Wikipedia, Google)",
        "Consulting a native speaker/Community member",
        "Books, articles, websites, or other reference materials (e.g., museum artifacts)",
        "AI tools for testing difficulty",
        "AI tools for brainstorming",
    ]
    short = [
        "Personal\nknowledge", "Online\nencyclopedia",
        "Native speaker/\ncommunity", "Books/\narticles",
        "AI: testing", "AI: brainstorming",
    ]
    rc = Counter()
    for v in df["resources_used"].dropna():
        for item in split_multiselect(str(v)):
            rc[item] += 1

    vals = [rc.get(o, 0) for o in fixed]
    order = sorted(zip(short, vals), key=lambda x: -x[1])
    labs, vs = zip(*order)
    colors = [PALETTE["vermillion"] if v == max(vs) else PALETTE["bluish_green"] for v in vs]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(labs[::-1], vs[::-1], color=colors[::-1])
    ax.set_xlabel(f"Respondents (of {len(df)})")
    ax.set_title(
        "Resources Used While Writing Riddles\n"
        'Survey Q: "What resources did you use? Select all that apply."',
        fontsize=9,
    )
    for i, v in enumerate(vs[::-1]):
        ax.text(v + 0.2, i, str(v), va="center", fontweight="bold")

    save_figure(fig, FIGURES_DIR / "resources_used")



