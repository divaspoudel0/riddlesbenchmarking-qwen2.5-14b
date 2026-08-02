# Getting results faster and cheaper

The runner sends requests **one at a time**. This package adds three faster
paths, all sharing one CacheSaver-compatible cache layer so results are
interchangeable with a normal `cache_enabled` run.

## Pick a path

| You want… | Providers | How |
| --- | --- | --- |
| **Concurrency inside a normal run** | Cohere, vLLM and OpenRouter (OpenAI-compatible) | set `batch_mode: true` + `batch_size: N` in the config |
| **Pre-fill the cache concurrently**, then run | Cohere, vLLM, OpenRouter, Together | `python -m riddles_framework.batch.fill --workers N` |
| **Offline Batch API (~50% cheaper)** | OpenAI, Anthropic, Gemini | `python -m riddles_framework.batch.fill --backend batch` |

Concurrency gives an **N× speedup** bounded by the provider's rate limit. The
Batch APIs are offline (minutes–hours) but cheaper and high-throughput. Cohere, vLLM
and OpenRouter have **no chat Batch API**, so concurrency is their fast path.

## How it works (shared foundation)

CacheSaver's `SyncWrapper` runs an asyncio pipeline (per-key locks, an online
batcher) via `asyncio.run` per call — it is serial and **not thread-safe**
(verified: concurrent threads deadlock). So everything here **bypasses the
wrapper** and reads/writes the underlying `diskcache` directly via
`cache_compat.py`, reproducing CacheSaver's exact key and per-provider entry
format. Verified against real run caches: the reconstructed key matches, and a
live CacheSaver client reads our entries as plain hits.

Consequences:
- A fast run populates the cache; a later normal run reads every prompt as a hit
  (no re-billing). The two are fully interchangeable.
- Only cache **misses** are fetched. Changing the prompt/model/params changes the
  key, so a different config legitimately re-fills.

---

## Path 1 — `batch_mode` (concurrency inside the run)

For OpenAI-compatible providers (Cohere, OpenRouter), the adapter's
`generate_batch` runs `batch_size` requests concurrently through a plain
thread-safe client, reading/writing the cache directly. Just configure it:

```yaml
batch_mode: true
batch_size: 12          # concurrency
model_spec:
  capabilities:
    supports_batch: true   # required, else the runner refuses batch_mode
```

Then run the CLI normally — no extra step:

```bash
uv run python -m riddles_framework.cli --config configs/benchmark_v0/cohere_tiny_aya.yaml
```

Implemented in `models/concurrent_batch.py` + the `generate_batch` overrides in
`cohere_adapter.py` / `openrouter_adapter.py`.

## Path 2 — `batch.fill` (pre-fill, then run)

Fills the cache out-of-band, then a normal run reads hits. Two backends, auto-
selected by provider (override with `--backend`):

```bash
# OpenAI-compatible -> concurrent real-time (threadpool)
python -m riddles_framework.batch.fill --config configs/benchmark_v0/cohere_tiny_aya.yaml --workers 12

# OpenAI / Anthropic / Gemini -> provider Batch API (offline, ~50% cheaper)
python -m riddles_framework.batch.fill --config configs/benchmark_v0/gpt55_high.yaml --backend batch

# count misses without making any calls
python -m riddles_framework.batch.fill --config <cfg> --dry-run

# then the normal run is instant (100% cache hits)
uv run python -m riddles_framework.cli --config <same cfg>
```

Flags: `--backend auto|threadpool|batch`, `--workers N` (threadpool concurrency),
`--poll N` (batch poll interval, s), `--dry-run`.

---

## Provider support

| Provider | Concurrency (`batch_mode` / `--workers`) | Batch API (`--backend batch`) |
| --- | --- | --- |
| OpenAI | — (use Batch) | ✅ |
| Anthropic | — (use Batch) | ✅ |
| Gemini | — (use Batch) | ✅ |
| Cohere | ✅ | ❌ (no chat Batch API) |
| OpenRouter | ✅ | ❌ |
| Together | ✅ (via `--workers`) | ❌ |

## Cache key + entry format (validated against real caches)

| Provider | Cache key | Cache entry |
| --- | --- | --- |
| OpenAI / Cohere / OpenRouter / Together | default hash | `openai…ChatCompletion` |
| Anthropic | default hash | `anthropic…Message` |
| Gemini | custom hash (≡ default when no `config`) | `google…GenerateContentResponse` |

## Files

| File | Role |
| --- | --- |
| `cache_compat.py` | shared diskcache read/write + per-provider keys |
| `threadpool.py` | concurrent pre-fill for OpenAI-compatible providers |
| `openai_batch.py` / `anthropic_batch.py` / `gemini_batch.py` | provider Batch APIs |
| `fill.py` | CLI driver (`python -m riddles_framework.batch.fill`) |
| `../models/concurrent_batch.py` | in-run `batch_mode` concurrency (used by the adapters) |

## Test status

- `cache_compat`, `threadpool`, `fill`, `batch_mode` concurrency — unit/mock-tested.
- All four real-call paths validated live end-to-end on a small slice: `batch_mode`
  (Cohere), and the Batch APIs (OpenAI / Anthropic / Gemini).
- Gemini matches responses by per-request metadata, not order (Gemini doesn't
  guarantee inline ordering); validated against google-genai 2.8.0 — re-check its
  batch surface if you upgrade.
