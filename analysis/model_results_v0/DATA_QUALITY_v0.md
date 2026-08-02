# Data quality report: v0 model runs

Generated 2026-07-31 by data_quality_report.py. Do not edit by hand; rerun the script.

Rows: 127571, models: 29, communities: 44, conditions: 1

## Per-model response health

unparsed = response present but no answer extractable (mostly reasoning that never reaches the JSON answer). truncated = unparsed with >= 4000 output tokens, i.e. the model hit the shared token budget before answering.

| model | rows | empty | unparsed | truncated | judge correct | judge unknown |
|---|---|---|---|---|---|---|
| Amazon Nova Lite v1 | 4399 | 0 | 1 | 0 | 450 | 24 |
| Amazon Nova Micro v1 | 4399 | 0 | 14 | 0 | 279 | 71 |
| Apertus-70B-Instruct-2509 | 4399 | 1 | 77 | 2 | 492 | 84 |
| Apertus-8B-Instruct-2509 | 4399 | 0 | 4 | 0 | 245 | 1 |
| Apertus-v1.5-70B | 4399 | 0 | 0 | 0 | 642 | 0 |
| Apertus-v1.5-8B | 4399 | 0 | 3 | 1 | 357 | 17 |
| Cohere Command A Plus | 4399 | 0 | 1136 | 1122 | 1089 | 127 |
| DeepSeek V4 Flash | 4399 | 0 | 3 | 0 | 1306 | 5 |
| EuroLLM-22B-Instruct-2512 | 4399 | 0 | 19 | 10 | 531 | 1 |
| GPT5.5 [high] | 4399 | 527 | 0 | 0 | 2542 | 0 |
| GPT5.5 [none] | 4399 | 130 | 0 | 0 | 2581 | 1 |
| GPT5.5-search (search-enabled, separate category) | 4399 | 0 | 0 | 0 | 2186 | 41 |
| Gemini 2.5 Flash | 4399 | 0 | 2 | 0 | 1638 | 18 |
| Gemini 2.5 Flash Lite | 4399 | 0 | 4 | 2 | 1129 | 3 |
| Gemma 4 31B IT | 4399 | 0 | 1 | 0 | 1275 | 19 |
| Mistral Large 3 | 4399 | 0 | 0 | 0 | 1308 | 0 |
| OLMo-3-32B-Think | 4399 | 0 | 407 | 393 | 407 | 102 |
| Qwen-SEA-LION-v4.5-27B-IT | 4399 | 45 | 447 | 445 | 1100 | 17 |
| Qwen/Qwen3.5-0.8B | 4399 | 0 | 8 | 0 | 14 | 6 |
| Qwen3.5 27B | 4399 | 0 | 1 | 1 | 892 | 34 |
| Tiny-Aya earth | 4399 | 0 | 17 | 12 | 209 | 0 |
| Tiny-Aya fire | 4399 | 0 | 20 | 19 | 207 | 1 |
| Tiny-Aya global | 4399 | 0 | 6 | 6 | 226 | 0 |
| Tiny-Aya water | 4399 | 0 | 18 | 18 | 204 | 0 |
| claude-opus-4-7 [none] | 4399 | 83 | 0 | 0 | 2006 | 13 |
| claude-opus-4-7 [thinking] | 4399 | 94 | 0 | 0 | 2211 | 148 |
| deepseek-v4-pro | 4399 | 1 | 3 | 3 | 1981 | 60 |
| deepseek-v4-pro-thinking | 4399 | 69 | 4 | 2 | 2169 | 30 |
| gemini-3.1-pro-preview | 4399 | 0 | 90 | 90 | 2783 | 76 |

## Notable findings

Threshold: models with more than 5% of rows empty or unparsed.

- Cohere Command A Plus: 25.8% of rows have no extractable answer (1122 of 1136 unparsed rows hit the token budget).
- GPT5.5 [high]: 12.0% of rows have no extractable answer (0 of 0 unparsed rows hit the token budget).
- OLMo-3-32B-Think: 9.3% of rows have no extractable answer (393 of 407 unparsed rows hit the token budget).
- Qwen-SEA-LION-v4.5-27B-IT: 11.2% of rows have no extractable answer (445 of 447 unparsed rows hit the token budget).

## Version notes (hand-maintained context, append per version)

- v0: Command A+ July 13 rerun fixed earlier empty responses (404s) but 1,122 of its 1,136 unparsed rows hit the 4,096 token budget mid-reasoning; kept as-is for v0, scored as format failures, flagged to leads 15 Jul 2026.
- v0: Amazon Nova Micro emits pseudo-JSON with single-quoted values; handled in load_results.extract_answer.
- v0: Qwen-SEA-LION and OLMo-3-32B-Think spill reasoning and truncate before answering on a subset of rows; treated as genuine no-answers.
- v0: judge abstention detection (NO_ANSWER_PHRASES_RAW) covers ~6 of 30+ benchmark languages; honest-uncertainty rates are lower bounds. Raised with Abdellah 19 Jul 2026; rerun scoring once the phrase list is extended.
- v0: follow-up audit (22 Jul 2026) found zero non-English abstention phrases in v0 responses. Models abstain in English even when riddles are presented in other languages, so the language-coverage caveat above is softer than first feared: English-only detection appears to capture v0 abstentions in practice.
- v0: 639 answers are literal prompt-template echoes (530 `<your_riddle_answer>`, 25 `<answer>`, 84 `...`), concentrated in three runs: OLMo-3-32B-Think (519), Qwen-SEA-LION-v4.5-27B-IT (88), Command A+ (32). 635 scored incorrect, 4 leaked through as correct. These are format failures, not knowledge failures; because they cluster in two or three runs they depress those models' leaderboard rows specifically. Now reclassified analysis-side (metrics.TEMPLATE_ECHO_ANSWERS): counted as format failures, never correct, so they move out of the 'incorrect' bucket and flag the three runs as format-failure floors. Accuracy is essentially unchanged (only 4 coincidental matches removed). A judge-side placeholder reject would supersede this.
- v0: GPT5.5-search (03_gpt-5.5-search, added 22 Jul 2026) ran with web search enabled. It is a SEPARATE evaluation category (eval_category=search_enabled in the tidy frame): open-web retrieval is not comparable to closed-book recall, so figures mark it with a distinct marker and a '(search)' label suffix. Clean run (4,400/4,400 parsed JSON), 49.7% raw match, below both closed-book GPT5.5 variants; flag to leads.
- v0: riddle spanish_cuba_history_016 is excluded from analysis (EXCLUDED_RIDDLES in load_results). The v0 text was wrong; the contributor corrected the source row and it is re-evaluated fresh in v2. Every model's answers to it are answers to the wrong riddle, so they are dropped from scoring. Denominators are 4,399 riddles for Spanish (Cuba); the frozen run files are untouched. See RIDDLE_CORRECTIONS.md (flagged 23 Jul 2026).
- v0: 4 Apertus runs (swiss-ai, folders 30-33) added 31 Jul 2026 by Hannah: Apertus 8B and 70B in v1 (Instruct-2509) and v1.5. Closed-book, full v0 coverage (4,400 riddles each, ~all success). Accuracy 5.6% (v1 8B) to 14.6% (v1.5 70B); v1.5 > v1 and 70B > 8B. Leaderboard now 29 runs; top unchanged.
