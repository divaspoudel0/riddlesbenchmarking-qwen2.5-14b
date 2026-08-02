"""Evaluation helpers for the riddles benchmark.

This package bundles two scorers for a framework run's ``results.jsonl``:

- ``reference_heuristic_judge`` — deterministic reference-answer matching
  (no LLM call).
- ``llm_as_a_judge`` / ``llm_judge_run`` — lenient LLM-as-a-judge scoring.
"""

from evals.llm_as_a_judge import (
    JUDGE_OUTPUT_SCHEMA,
    JUDGE_SYSTEM_PROMPT,
    TARGET_MODELS,
    build_judge_messages,
    build_openrouter_payload,
    export_model_registry,
    models_by_alias,
    normalize_judge_instance,
    select_route,
)

__all__ = [
    "JUDGE_OUTPUT_SCHEMA",
    "JUDGE_SYSTEM_PROMPT",
    "TARGET_MODELS",
    "build_judge_messages",
    "build_openrouter_payload",
    "export_model_registry",
    "models_by_alias",
    "normalize_judge_instance",
    "select_route",
]
