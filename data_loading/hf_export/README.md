---
license: cc-by-4.0
pretty_name: Multicultural Riddles Benchmark
language:
- aeb
- apc
- apd
- ary
- arz
- asm
- bel
- ben
- bug
- bul
- cat
- deu
- eng
- fra
- gaz
- guj
- hun
- ind
- ita
- jpn
- kan
- kok
- ltz
- lug
- mal
- mar
- mog
- myx
- nep
- nld
- pes
- pol
- por
- rus
- sin
- snd
- spa
- srp
- swa
- tam
- tel
- tha
- tur
- ukr
- urd
- uzb
- vie
- yor
- yue
- zho
- zsm
task_categories:
- question-answering
multilinguality:
- multilingual
size_categories:
- 1K<n<10K
annotations_creators:
- expert-generated
language_creators:
- expert-generated
source_datasets:
- original
tags:
- riddles
- cultural-reasoning
- cultural-knowledge
- multilingual
- multicultural
- community-curated
- low-resource-languages
configs:
- config_name: default
  data_files:
  - split: test
    path: data/test-*
---

# Multicultural Riddles Benchmark

A community-built benchmark of original cultural riddles spanning **61 communities across 51 languages**. Each riddle describes something without ever naming it, so answering it requires genuine cultural knowledge rather than translation or web search. A native speaker would recognise the answer instantly; a model only succeeds if it carries that culture's knowledge.

## Dataset summary

Most multilingual benchmarks are written in English and translated outward, which tests language but not culture. This benchmark inverts that. Native speakers from each community write their own riddles from scratch, using a shared English framework only as a starting point, not as a source to translate. The riddles are intentionally indirect: they use local nicknames, synonyms, and oblique description so that the answer cannot be reached by recognising a keyword. The goal is depth of cultural understanding, measured where today's models tend to be fluent but shallow.

This is the pilot release: **6100 riddles** across 61 communities, of which 1220 come from community-chosen wildcard topics. It is intended for evaluation only.

## Why riddles

A riddle names nothing. "This red-crossed sphere's juice is not sweet for your stomach" means nothing to a search engine, but every Hungarian recognises Unicum, a famous bitters. A model that only knows the formal name misses it entirely. Because each riddle is original, unpublished, and culturally specific, it resists both memorisation and reverse-engineering from training data, which gives the benchmark a longer useful life than fact-lookup tasks.

## Languages and communities

The base unit is the present-day national-linguistic community, for example Spanish from Argentina or Bengali from India. 61 communities are represented across 51 languages. Languages outnumber communities because several communities share a language: Argentine, Cuban, and Peruvian riddles are all in Spanish but draw on three different cultures. That separation is the point of the benchmark.

The benchmark grows over time. Each community carries a `release_version` marking the collection round it entered in (`v0` is the first round, `v1` the next, and so on), so results can be compared across releases.

## Dataset structure

### Data fields

| Field | Type | Description |
|---|---|---|
| `riddle_id` | string | Stable unique id, `{community}_{topic}_{number}`. |
| `language` | string | ISO 639-3 code of the riddle's language. |
| `community` | string | Cultural community, `{culture}_{country}` (e.g. `tamil_india`). |
| `release_version` | string | Collection round the community was added in (`v0`, `v1`, ...). |
| `topic` | string | Topic category the riddle belongs to. |
| `is_wildcard` | bool | True if the riddle is from a community-chosen wildcard topic. |
| `riddle_original` | string | The riddle in its original language. |
| `riddle_english` | string | English translation of the riddle. Reference only; may be null. |
| `reference_answer_original` | string | Gold answer in the original language. |
| `reference_answer_english` | string | English translation of the answer. May be null. |
| `riddle_hint` | string | Optional hint. May be null. |
| `riddle_note` | string | Optional note or comment from the author. May be null. |
| `author_credit` | string | Contributor(s) who wrote the riddle. |

### Splits

A single `test` split of 6100 rows. `community`, `language`, and `topic` are columns to filter on, not separate splits.

## Loading the dataset

```python
from datasets import load_dataset

ds = load_dataset("CohereLabsCommunity/multicultural-riddles-benchmark", split="test")

# filter to one community
tamil = ds.filter(lambda r: r["community"] == "tamil_india")

# filter to one language
egyptian_arabic = ds.filter(lambda r: r["language"] == "arz")
```

## Curation

Every riddle is original human writing. Contributors are native speakers who write for their own community, following a shared format of topics and questions per topic. AI tools may be used for brainstorming or to test how hard a riddle is for a model, but the riddles themselves are written by people, not generated. English translations are provided for human reference and documentation only, never to present the riddle to a model. All riddles are free of personally identifiable information.

## Intended use and terms

Released under **CC-BY-4.0**: you may share and adapt the data, including commercially, with attribution.

**This data must not be used to train, fine-tune, or distill models, nor as seeds for synthetic data generation.** It is an evaluation benchmark. Using it as training data defeats its purpose and contaminates future measurement. Please respect this restriction in addition to the license.

## Contributors

This benchmark was proposed by **Károly Boczka** and **Julia Kreutzer**, and built by native-speaker contributors across the Cohere Labs Community.

> Note: the per-community credits below are derived from contributor-supplied author fields and are provisional pending contributor confirmation before any public release.

- **afaan_oromo_oromo**: Bontu Fufa, Debela Yadeta
- **arabic_egypt**: Farah Abdou, Nadine Elframawy, Rawan Elframawy
- **arabic_lebanese**: Adnan El Assadi
- **arabic_morocco**: Abdellah El Mekki, Abderrahmane Issam, Zakaria Baannou
- **arabic_sudan**: abdelhadi Osama, Eithar Ismail, Wafaa Mohammed
- **arabic_syria**: Yusser Al Ghussin, Zena AL Khalili
- **assamese_india**: Angana Borah, Dipti Borah Hazarika, Mina Saikia, Prasanta Borah
- **belarusian_belarus**: Ilia Afanasev, Iryna Balunenka, Oksana Volchek, Vladislav Poritski
- **bengali_bangladesh**: Ahanaf Aziz, Istiak, Nazia Tasnim
- **bengali_india**: Ankita Maity, Ruchira, Souvik
- **brazilian_portuguese**: Daniel Souza, facms, FelipeBocaJR, its_assisgab, João Paulo, Juliana Carvalho, Lucas Resck, mrncstt, Pedro Delgado
- **bugisnese_indonesia**: Ahmad Mufli Ramadhan
- **bulgarian_bulgaria**: Ralitza Rizova
- **cantonese_china**: Fengran Mo, Jinghan Zhang
- **catalan_catalonia**: Aleix, Irene, Javi, Marc, Ona
- **chinese_china**: Stephy Chen
- **chinese_malaysia**: Nancy F. Chen, Zhengyuan Liu
- **chinese_simplified_china**: Bin, Cecilia, Charles, Di, Kaiser, Lingbo, Tenney
- **chinese_singapore**: Ruiyang Tan, Weihua Zheng
- **dutch_netherlands**: Charlotte, David, Mike, Rochelle
- **english_canada**: Jane Smith, Julia Kreutzer, Madeline Smith, Matt Bobkin
- **english_usa**: Ananya Sahu, Henry Gagnier, Jonathan Swindell, Sajag Swami, Swati Rajwal
- **french_canada**: Lauren, Micol
- **french_france**: BryanBradfo, Wafa Aissa
- **german_germany**: Diana Kozachek, Julia Kreutzer
- **gujarati_india**: Amit Agarwal, Fenal Ilasariya, Hitesh Patel
- **hungarian_hungary**: Károly Boczka
- **indonesian_indonesia**: Ahmad Mufli Ramadhan, Muhammad Ravi Shulthan Habibi
- **italian_italy**: Lisa Alazraki, Marco De Santis
- **japanese_japan**: Reuben
- **kannada_india**: Emile Anand, Vanya Bannihatti Kumar
- **konkani_india**: prerana rane, Vivek Silimkhan
- **luganda_uganda**: Alex Gimei
- **lumasaba_uganda**: Alex Gimei
- **luxembourgish_luxembourg**: Cedric Lothritz, Fred Philippy
- **malay_malaysia**: Roy Ka-Wei Lee
- **malayalam_india**: Arya Hariharan, Arya Suneesh
- **marathi_india**: Rushikesh Zawar, Yash Bagla
- **mongondow_indonesia**: Ahmad Mufli Ramadhan
- **nepali_nepal**: Dikshya Poudel, Divas Poudel, jebish7
- **persian_iran**: Amin Shfaiei, Aylin Naebzadeh, Hamidreza Saffari, Houman Mehrafarin, Masoumeh Javadi Zarnaghi, Mehrnaz Mofakhami, Melika Davoodzadeh, Pouya Sadeghi, Sara Rajaee, Sarah Bahrami
- **polish_poland**: Dominik Krzeminski, Joanna Radoła
- **portuguese_portugal**: diogom
- **russian_russia**: Anastasiia Nikitina, Andrei Nikitin, Dina Pisarevskaya, Galina Kozulina, Sergey Sedov
- **serbian_serbia**: Danka Jokić, Milica Andrić, Nebojša Damnjanović, Toma Knežević
- **sindhi_india**: Naman Bhatia
- **sinhala_sri_lanka**: Sayuru
- **spanish_argentina**: Leandro Cossio, Matías Ávalos, Silvia Fernández
- **spanish_cuba**: Eduardo Sánchez, Fernando Ortiz, Rogelio Díaz Castillo
- **spanish_peru**: David Quispe-Castillo, Fabrizzio Marin Colquichagua, Luis Fernando Solis Navarro
- **swahili_kenya**: Loice Nanyanga, Priscilla, Valen
- **tamil_india**: Vinod
- **telugu_india**: Akhil Eppa, Indu, Jayanth Krishna Chundru, Leema, Manaswitha Sunkara, Prahitha Movva, Salman Khan, Tejaswi Sunkara
- **thai_thailand**: Kanison Tungsupakij, Patteera Triamamornwooth, Punnatud Duengkae, Rapol Tongchenchitt, Warit Lekmuenwai
- **tunisian_arabic_tunisia**: Safa Faraa, Wafa Aissa
- **turkish_turkey**: Ceren Berk
- **ukrainian_ukraine**: Hanna Yukhymenko, Olena Bugaiova, Yurii Paniv
- **urdu_pakistan**: Muhammad Saad Umar
- **uzbek_uzbekistan**: Abdumutalib Begmuratov
- **vietnamese_vietnam**: Christian Hoang, My Chiffon Nguyen, Van Ngo
- **yoruba_nigeria**: Esther Adenuga, Joy Olusanya, Seun Ajayi, Yusuf Ismail

## Citation

```bibtex
@misc{multicultural_riddles_2026,
  title        = {Multicultural Riddles Benchmark},
  author       = {Boczka, K{\'a}roly and Kreutzer, Julia and the Cohere Labs Community},
  year         = {2026},
  publisher    = {Hugging Face},
  howpublished = {\url{https://huggingface.co/datasets/CohereLabsCommunity/multicultural-riddles-benchmark}}
}
```
