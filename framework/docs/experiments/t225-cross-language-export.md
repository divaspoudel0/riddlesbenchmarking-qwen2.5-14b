# T2.2.5 Cross-language Export Verification

Dataset: `smoke_test_25` (25 rows, languages: arz, eng, rus, tam, zho)
Versions: transformers=5.10.1, cachesaver=0.0.6
API keys present: none

| Provider | Category | Condition | Ran | Rows | Statuses | Languages | Tokens | Export |
|---|---|---|---|---|---|---|---|---|
| dummy | dummy | baseline | yes | 25 | success:25 | arz, eng, rus, tam, zho | no | OK |
| dummy-json | dummy | response_format=json | yes | 25 | success:25 | arz, eng, rus, tam, zho | no | OK |
| dummy-english | dummy | riddle_language_presented=english | yes | 25 | success:25 | arz, eng, rus, tam, zho | no | OK |
| dummy-hint | dummy | is_hint_provided=True | yes | 25 | success:25 | arz, eng, rus, tam, zho | no | OK |
| local-hf | local | baseline | yes | 25 | success:25 | arz, eng, rus, tam, zho | yes | OK |
| cohere-api | api | baseline | SKIPPED (COHERE_API_KEY not set) | - | - | - | - | - |
| together-aggregator | aggregator | baseline | SKIPPED (TOGETHER_API_KEY not set) | - | - | - | - | - |
