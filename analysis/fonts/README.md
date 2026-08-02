# Vendored fonts

Noto fonts vendored so non-Latin text in figures renders identically on any
machine (no reliance on macOS system fonts like Arial Unicode MS). They are
registered automatically by `style.apply_style()` and sit in the serif
fallback chain (`style.SERIF_STACK`); matplotlib >= 3.6 falls back per glyph.

All fonts are regular weight (400) only, which is all the figures use.

| File | Family name | Covers |
|---|---|---|
| NotoSerif-Regular.ttf | Noto Serif | Latin, Latin-ext, Cyrillic (+ext), Greek (+ext), Vietnamese |
| NotoSerifSC-Regular.ttf | Noto Serif SC | CJK, simplified and traditional codepoints |
| NotoNaskhArabic-Regular.ttf | Noto Naskh Arabic | Arabic incl. Persian and Urdu codepoints |
| NotoSerifBengali-Regular.ttf | Noto Serif Bengali | Bengali |
| NotoSerifDevanagari-Regular.ttf | Noto Serif Devanagari | Marathi, Nepali, Konkani |
| NotoSerifMalayalam-Regular.ttf | Noto Serif Malayalam | Malayalam |
| NotoSerifTamil-Regular.ttf | Noto Serif Tamil | Tamil |
| NotoSerifTelugu-Regular.ttf | Noto Serif Telugu | Telugu |
| NotoSerifSinhala-Regular.ttf | Noto Serif Sinhala | Sinhala |
| NotoSerifThai-Regular.ttf | Noto Serif Thai | Thai |
| NotoSansBuginese-Regular.ttf | Noto Sans Buginese | Lontara (Bugis, Makassar); Noto has no serif cut for this script |

## Provenance

Extracted from Fontsource npm packages (`@fontsource/noto-serif-tamil` etc.,
v5.3.0, 22 Jul 2026), which repackage Google's Noto releases. The 400-normal
woff2 subset files were converted to TTF with fontTools (matplotlib cannot
read woff2). Multi-subset families (Noto Serif, Noto Serif SC) were merged
into one TTF per family with `fontTools.merge`, because matplotlib maps one
font file per family name and cannot combine unicode-range chunks the way a
browser does. The merged SC font's name table was normalized to family
"Noto Serif SC", weight Regular.

License: SIL Open Font License 1.1, see OFL.txt. Copyright The Noto Project
Authors.
