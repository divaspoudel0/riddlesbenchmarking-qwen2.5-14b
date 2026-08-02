"""Central figure style for the analysis pipeline — colors + fonts in one place.

Every plotting script should do this once, up front::

    from analysis.style import apply_style, PALETTE, CONDITION_COLORS, save_figure
    apply_style()

...then pull colors from the named maps below (never hard-code hex in a plot).
That keeps every published figure visually consistent and lets us restyle the
whole paper by editing this one file.

* **Library:** matplotlib (+ seaborn for statistical plots). Both honor the
  ``rcParams`` set here, so this file governs seaborn output too.
* **Fonts — "LaTeX serif" without ``usetex``.** We do NOT enable
  ``text.usetex`` (needs a local TeX install and chokes on non-Latin Unicode).
  Instead we use a serif *fallback chain*: STIX Two Text (a Times/Computer-
  Modern-adjacent serif bundled with matplotlib, so it's reproducible on any
  machine) for Latin + math, falling back per-glyph (matplotlib >= 3.6) to
  Noto Serif / DejaVu so the benchmark's many writing systems never render as
  missing-glyph boxes. Math uses the Computer Modern set for the LaTeX look.
* **Colors — colorblind-safe.** The categorical palette is Okabe & Ito's
  8-colour set, the de-facto standard for accessible scientific figures.
  Heatmaps (e.g. accuracy grids) use a perceptually-uniform sequential map.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib as mpl


# --------------------------------------------------------------------------- #
# Colors
# --------------------------------------------------------------------------- #
# Okabe-Ito colorblind-safe qualitative palette. Reference:
# https://jfly.uni-koeln.de/color/  (Okabe & Ito, 2008)
PALETTE: dict[str, str] = {
    "black": "#000000",
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "bluish_green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "reddish_purple": "#CC79A7",
    # neutral greys for gridlines / annotations / reference lines
    "grey": "#7F7F7F",
    "light_grey": "#CCCCCC",
}

# Default categorical cycle (used for e.g. one line/bar per model). Drawn from
# the Okabe-Ito set, ordered for maximum separation of the first few entries.
CATEGORICAL_CYCLE: list[str] = [
    PALETTE["blue"],
    PALETTE["vermillion"],
    PALETTE["bluish_green"],
    PALETTE["orange"],
    PALETTE["reddish_purple"],
    PALETTE["sky_blue"],
    PALETTE["yellow"],
    PALETTE["black"],
]

# Semantic colors for the three supported benchmark conditions
# (see framework: source_no_hint / source_with_hint / english_no_hint).
CONDITION_COLORS: dict[str, str] = {
    "source_no_hint": PALETTE["blue"],
    "source_with_hint": PALETTE["sky_blue"],
    "english_no_hint": PALETTE["vermillion"],
}

# Sequential map for continuous quantities (accuracy heatmaps, etc.).
# "viridis" is perceptually uniform and colorblind-friendly.
SEQUENTIAL_CMAP = "viridis"
# Diverging map for signed quantities (e.g. delta vs. a baseline).
DIVERGING_CMAP = "vlag"  # seaborn-provided; falls back to "coolwarm" if missing


# --------------------------------------------------------------------------- #
# Fonts
# --------------------------------------------------------------------------- #
# Serif fallback chain: first font present that has the glyph wins
# (matplotlib >= 3.6 does per-glyph fallback down this list). The catch: a
# fallback only helps if a font actually covering that script is installed.
# For reproducible non-Latin rendering across machines, vendor the open-licensed
# Noto fonts into ``analysis/fonts/`` and call :func:`register_fonts` before
# :func:`apply_style` — the "Noto ..." entries below then take precedence over
# the system fallbacks. Until then, "Arial Unicode MS" (broad macOS system font)
# is the practical catch-all so labels don't render as missing-glyph boxes.
SERIF_STACK: list[str] = [
    "STIX Two Text",     # bundled with matplotlib; Times/CM-adjacent serif (Latin + math)
    "Times New Roman",
    # Vendored in analysis/fonts/ (see fonts/README.md); registered by
    # apply_style via register_fonts so figures render identically off-Mac.
    "Noto Serif",            # Latin ext + Cyrillic + Greek + Vietnamese
    "Noto Serif SC",         # CJK (simplified + traditional codepoints)
    "Noto Naskh Arabic",     # Arabic incl. Persian/Urdu codepoints
    "Noto Serif Bengali",
    "Noto Serif Devanagari",  # Marathi, Nepali, Konkani
    "Noto Serif Malayalam",
    "Noto Serif Tamil",
    "Noto Serif Telugu",
    "Noto Serif Sinhala",
    "Noto Serif Thai",
    "Noto Sans Buginese",    # Lontara; no serif cut exists
    "Arial Unicode MS",  # broad macOS system fallback: Arabic/Devanagari/CJK/Hebrew/...
    "DejaVu Serif",      # matplotlib's always-present last resort (Latin/Greek/Cyrillic)
]


def register_fonts(font_dir: str | Path = Path(__file__).parent / "fonts") -> list[str]:
    """Register every .ttf/.otf under ``font_dir`` with matplotlib.

    Call this BEFORE :func:`apply_style` to make vendored fonts (e.g. the Noto
    family) available by name, so figures render identically on any machine
    regardless of what's installed system-wide. Returns the font family names
    that were registered. A missing directory is a no-op.
    """
    from matplotlib import font_manager as fm

    font_dir = Path(font_dir)
    registered: list[str] = []
    if not font_dir.exists():
        return registered
    for path in sorted(font_dir.rglob("*")):
        if path.suffix.lower() in {".ttf", ".otf"}:
            fm.fontManager.addfont(str(path))
            registered.append(fm.FontProperties(fname=str(path)).get_name())
    return registered


# --------------------------------------------------------------------------- #
# rcParams
# --------------------------------------------------------------------------- #
def _rc_params() -> dict[str, object]:
    """The full rcParams dict applied by :func:`apply_style`."""
    # Per-glyph font fallback (matplotlib >= 3.6) only walks the list in
    # ``font.family``; with ``font.family = "serif"`` matplotlib resolves
    # ``font.serif`` to a SINGLE font and non-Latin glyphs render as tofu.
    # So pass the concrete stack as the family list, filtered to families
    # actually installed/registered (missing names would just log findfont
    # warnings on machines without e.g. Times New Roman).
    from matplotlib import font_manager as fm

    installed = {f.name for f in fm.fontManager.ttflist}
    family = [name for name in SERIF_STACK if name in installed] or ["serif"]
    return {
        # --- fonts ---
        "font.family": family,
        "font.serif": SERIF_STACK,
        "mathtext.fontset": "cm",      # Computer Modern math -> LaTeX look
        "axes.unicode_minus": False,   # use ASCII '-'; safe across fallbacks
        # --- type sizes (tuned for a single-column paper figure) ---
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "figure.titlesize": 11,
        # --- color cycle ---
        "axes.prop_cycle": mpl.cycler(color=CATEGORICAL_CYCLE),
        # --- spines / grid: clean, light, publication-friendly ---
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": PALETTE["light_grey"],
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "axes.edgecolor": "#333333",
        "axes.linewidth": 0.8,
        # --- figure / saving: vector-first for print ---
        "figure.figsize": (3.5, 2.6),  # ~single column; override per figure
        "figure.dpi": 150,             # on-screen; savefig.dpi governs export
        "savefig.dpi": 300,
        "savefig.format": "pdf",
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42,            # embed TrueType (editable, no Type-3)
        "ps.fonttype": 42,
        "legend.frameon": False,
    }


def apply_style() -> None:
    """Apply the project figure style to the global matplotlib rcParams.

    Call once at the top of any plotting script, before creating figures.
    Also registers the vendored fonts in ``analysis/fonts/`` (no-op if the
    directory is missing), so callers don't need a separate
    :func:`register_fonts` call.
    """
    register_fonts()
    mpl.rcParams.update(_rc_params())


def color_for_condition(condition_id: str) -> str:
    """Return the semantic color for a benchmark condition id."""
    return CONDITION_COLORS.get(condition_id, PALETTE["grey"])


def set_color_cycle(colors: Iterable[str]) -> None:
    """Override the active categorical color cycle (e.g. a fixed model order)."""
    mpl.rcParams["axes.prop_cycle"] = mpl.cycler(color=list(colors))


def save_figure(fig, path: str | Path, **kwargs) -> Path:
    """Save a figure as a publication-ready vector file.

    Honors the rcParams above (300 dpi, tight bbox, embedded fonts). Pass e.g.
    ``save_figure(fig, "figs/accuracy")`` -> writes ``figs/accuracy.pdf``.
    """
    path = Path(path)
    if not path.suffix:
        path = path.with_suffix("." + str(mpl.rcParams["savefig.format"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, **kwargs)
    return path
