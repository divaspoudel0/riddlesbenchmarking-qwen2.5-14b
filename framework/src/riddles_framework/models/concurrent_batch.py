"""Concurrent, cache-aware ``generate_batch`` for OpenAI-compatible adapters.

The runner's ``batch_mode`` calls ``model.generate_batch(prompts)``. The default
(``base.py``) runs them serially. This helper runs them **concurrently** with a
thread pool — giving an N× speedup bounded by the provider's rate limit.

CacheSaver's ``SyncWrapper`` deadlocks under concurrent thread access (verified),
so we do NOT thread over it. Instead we use a plain, thread-safe OpenAI SDK
client and read/write CacheSaver's on-disk cache directly via
``batch.cache_compat`` — same key + entry format as the online path, so results
populate the cache for later ``cache_enabled`` runs and dedupe within the run.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ..constants import GenerationStatus
from ..schemas import GenerationResult
from ..utils import looks_like_refusal, safe_int
from ..batch.cache_compat import cache_lookup, cache_store, openai_request_key


def _result_from_completion(resp: Any) -> GenerationResult:
    text = None
    if getattr(resp, "choices", None):
        text = getattr(resp.choices[0].message, "content", None)
    usage = getattr(resp, "usage", None)
    status = GenerationStatus.SUCCESS
    if text is None or str(text).strip() == "":
        status = GenerationStatus.EMPTY
    elif looks_like_refusal(text):
        status = GenerationStatus.REFUSAL
    return GenerationResult(
        raw_response=text,
        status=status,
        input_tokens=safe_int(getattr(usage, "prompt_tokens", None)) if usage else None,
        output_tokens=safe_int(getattr(usage, "completion_tokens", None)) if usage else None,
        provider_details={"model": getattr(resp, "model", None), "id": getattr(resp, "id", None)},
    )


def openai_compatible_generate_batch(
    *,
    prompts: list[str],
    plain_client: Any,
    provider_model_name: str,
    cache_dir: str | None,
    max_output_tokens: int,
    response_format: str = "free_form",
    temperature: float | None = None,
    seed: int | None = None,
    model_params: dict[str, Any] | None = None,
    token_param: str = "max_tokens",
    max_workers: int | None = None,
) -> list[GenerationResult]:
    """Concurrently generate for every prompt, in input order.

    ``plain_client`` must be a thread-safe OpenAI SDK client (NOT a CacheSaver
    wrapper). When ``cache_dir`` is set, hits are served from cache and new
    results are written back; ``token_param`` matches the provider's create kwarg
    (``max_tokens`` for Cohere/OpenRouter).
    """
    def build_kwargs(prompt: str) -> dict[str, Any]:
        kw: dict[str, Any] = {
            "model": provider_model_name,
            "messages": [{"role": "user", "content": prompt}],
            token_param: max_output_tokens,
        }
        if response_format == "json":
            kw["response_format"] = {"type": "json_object"}
        if temperature is not None:
            kw["temperature"] = temperature
        if seed is not None:
            kw["seed"] = seed
        if model_params:
            kw.update(model_params)
        return kw

    def one(prompt: str) -> GenerationResult:
        kw = build_kwargs(prompt)
        key = openai_request_key(kw) if cache_dir else None
        if cache_dir:
            cached = cache_lookup(cache_dir, key)
            if cached:
                return _result_from_completion(cached[0])
        try:
            resp = plain_client.chat.completions.create(**kw)
        except Exception as exc:  # noqa: BLE001
            return GenerationResult(raw_response=None, status=GenerationStatus.ERROR,
                                    error_message=str(exc))
        if cache_dir:
            cache_store(cache_dir, key, resp)
        return _result_from_completion(resp)

    workers = max_workers or max(1, len(prompts))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(one, prompts))   # ex.map preserves input order
