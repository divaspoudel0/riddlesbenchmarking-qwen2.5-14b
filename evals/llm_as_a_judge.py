"""Bootstrap scaffold for LLM-as-a-judge on the riddles benchmark.

This is intentionally framework-level, not provider-specific. The full runner
is not built yet, so this file only defines the contracts we already know:

1. The input schema we expect from the pilot dataset / spreadsheet pipeline.
2. The judge prompt and structured judge output shape.
3. The model registry for planned benchmark models.
4. Provider routes, including OpenRouter where applicable and placeholders for
   direct APIs or local execution where that is not settled yet.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


RIDDLES_SHEET_NAME = "Riddles"

SPREADSHEET_COLUMNS = (
    "Number",
    "Topic",
    "Author",
    "Riddle (Original Language)",
    "Riddle (English Translation)",
    "Hints (Optional)",
    "Comments (Optional), e.g. about region/generation-specificity",
    "Reference Answer (Original)",
    "Reference Answer (English)",
    "Human Validator Name",
    "Human Answer (Original)",
    "Rating of Human Answer (0-2)",
    "Comment (Optional) about evaluation of human answer",
)

PILOT_DATASET_FIELDS = (
    "instance_result_id",
    "riddle_id",
    "created_at",
    "source_row_number",
    "language",
    "language_secondary",
    "community",
    "topic",
    "is_wildcard",
    "riddle_original",
    "riddle_english",
    "reference_answer_original",
    "reference_answer_english",
    "riddle_hint",
    "riddle_note",
    "author_credit",
    "human_validator_name",
    "human_answer_original",
    "human_answer_score",
    "human_answer_comment",
    "row_status",
    "raw_template_fields",
)

JUDGE_REQUIRED_FIELDS = (
    "riddle_id",
    "community",
    "topic",
    "riddle_original",
    "reference_answer_original",
)

JUDGE_SYSTEM_PROMPT = """You are grading a model answer to a cultural riddle.
Return strict JSON only.

Judge whether the candidate answer matches the reference answer. Be lenient to
inflection, capitalization, transliteration, and short synonymous surface
forms, but do not allow unrelated entities.
"""

JUDGE_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["correct", "partially_correct", "incorrect", "unclear"],
        },
        "score": {
            "type": "integer",
            "enum": [0, 1, 2, 3],
        },
        "matched_reference": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "score", "matched_reference", "reason"],
    "additionalProperties": False,
}

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_CHAT_COMPLETIONS_URL = f"{OPENROUTER_BASE_URL}/chat/completions"


@dataclass(frozen=True)
class ProviderRoute:
    provider: str
    model_name: str | None = None
    base_url: str | None = None
    api_style: str | None = None
    supports_reasoning_param: bool = False
    supports_search_toggle: bool = False
    supports_json_schema: bool = False
    notes: str = ""


@dataclass(frozen=True)
class JudgeModelSpec:
    alias: str
    owner_name: str | None = None
    reasoning_mode: str | None = None
    search_enabled: bool = False
    prompt_reasoning_variant: str | None = None
    temperature_default: float = 0.0
    routes: tuple[ProviderRoute, ...] = field(default_factory=tuple)
    notes: str = ""


TARGET_MODELS: tuple[JudgeModelSpec, ...] = (
    JudgeModelSpec(
        alias="GPT5.5-high",
        owner_name="Seun Ajayi",
        reasoning_mode="high",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="openai/gpt-5.5-pro",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_reasoning_param=True,
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="openai_direct",
                model_name="gpt-5.5-pro",
                api_style="responses_or_chat",
                supports_reasoning_param=True,
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="GPT5.5-none",
        owner_name="Seun Ajayi",
        reasoning_mode="none",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="openai/gpt-5.5",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_json_schema=True,
                notes="OpenRouter slug should be confirmed live.",
            ),
            ProviderRoute(
                provider="openai_direct",
                model_name="gpt-5.5",
                api_style="responses_or_chat",
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="GPT5.5-search",
        owner_name="Seun Ajayi",
        reasoning_mode="none",
        search_enabled=True,
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="openai/gpt-5.5",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_search_toggle=True,
                supports_json_schema=True,
                notes="Search route is a placeholder until tool wiring is defined.",
            ),
            ProviderRoute(
                provider="openai_direct",
                model_name="gpt-5.5",
                api_style="responses_or_chat",
                supports_search_toggle=True,
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="claude-opus-4-7-thinking",
        owner_name="Di",
        reasoning_mode="high",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="anthropic/claude-opus-4.7",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_reasoning_param=True,
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="anthropic_direct",
                model_name="claude-opus-4-7",
                api_style="messages",
                supports_reasoning_param=True,
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="claude-opus-4-7",
        owner_name="Luis",
        reasoning_mode="none",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="anthropic/claude-opus-4.7",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="anthropic_direct",
                model_name="claude-opus-4-7",
                api_style="messages",
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="claude-opus-4-7-search",
        owner_name="Di",
        reasoning_mode="none",
        search_enabled=True,
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="anthropic/claude-opus-4.7",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_search_toggle=True,
                supports_json_schema=True,
                notes="Search route is a placeholder until tool wiring is defined.",
            ),
            ProviderRoute(
                provider="anthropic_direct",
                model_name="claude-opus-4-7",
                api_style="messages",
                supports_search_toggle=True,
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="gemini-3.1-pro-preview",
        owner_name="Diana",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="google/gemini-3.1-pro-preview",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="google_direct",
                model_name="gemini-3.1-pro-preview",
                api_style="google_generate_content",
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="gemini-3.1-pro-preview-grounding",
        search_enabled=True,
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="google/gemini-3.1-pro-preview",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_search_toggle=True,
                supports_json_schema=True,
                notes="Grounding route is a placeholder until exact request shape is defined.",
            ),
            ProviderRoute(
                provider="google_direct",
                model_name="gemini-3.1-pro-preview",
                api_style="google_generate_content",
                supports_search_toggle=True,
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="deepseek-v4-pro-thinking",
        owner_name="Diana",
        reasoning_mode="high",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="deepseek/deepseek-v4-pro",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_reasoning_param=True,
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="deepseek_direct",
                model_name="deepseek-v4-pro",
                api_style="openai_compatible",
                supports_reasoning_param=True,
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="deepseek-v4-pro",
        owner_name="Diana",
        reasoning_mode="none",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="deepseek/deepseek-v4-pro",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="deepseek_direct",
                model_name="deepseek-v4-pro",
                api_style="openai_compatible",
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="gemma-4-31b",
        owner_name="Diana",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="google/gemma-4-31b-it",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="local_or_hosted",
                model_name="gemma-4-31b-it",
                api_style="openai_compatible_or_transformers",
                notes="Non-OpenRouter route placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="gemma-3-4b-it",
        owner_name="Mufli",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="google/gemma-3-4b-it",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="local_or_hosted",
                model_name="gemma-3-4b-it",
                api_style="openai_compatible_or_transformers",
                notes="Non-OpenRouter route placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="Qwen3-4B",
        owner_name="Mufli",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="qwen/qwen3-4b",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="local_or_hosted",
                model_name="qwen3-4b",
                api_style="openai_compatible_or_transformers",
                notes="Non-OpenRouter route placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="CohereLabs/tiny-aya-fire",
        owner_name="Ankita",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name=None,
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                notes="OpenRouter slug unknown.",
            ),
            ProviderRoute(
                provider="cohere_or_internal",
                model_name="tiny-aya-fire",
                api_style="provider_specific",
                notes="Non-OpenRouter placeholder route.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="CohereLabs/tiny-aya-earth",
        owner_name="Ankita",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name=None,
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                notes="OpenRouter slug unknown.",
            ),
            ProviderRoute(
                provider="cohere_or_internal",
                model_name="tiny-aya-earth",
                api_style="provider_specific",
                notes="Non-OpenRouter placeholder route.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="CohereLabs/tiny-aya-water",
        owner_name="Ankita",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name=None,
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                notes="OpenRouter slug unknown.",
            ),
            ProviderRoute(
                provider="cohere_or_internal",
                model_name="tiny-aya-water",
                api_style="provider_specific",
                notes="Non-OpenRouter placeholder route.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="command-a-plus-05-2026",
        owner_name="Micol",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name=None,
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                notes="OpenRouter slug unknown.",
            ),
            ProviderRoute(
                provider="cohere_direct",
                model_name="command-a-plus-05-2026",
                api_style="cohere_chat_or_generate",
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="CohereLabs/tiny-aya-global",
        owner_name="Ahanaf",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name=None,
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                notes="OpenRouter slug unknown.",
            ),
            ProviderRoute(
                provider="cohere_or_internal",
                model_name="tiny-aya-global",
                api_style="provider_specific",
                notes="Non-OpenRouter placeholder route.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="EuroLLM",
        owner_name="diogom",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name=None,
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                notes="OpenRouter availability unknown.",
            ),
            ProviderRoute(
                provider="local_or_hosted",
                model_name="eurollm",
                api_style="openai_compatible_or_transformers",
                notes="Non-OpenRouter placeholder route.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="SEA-LION",
        owner_name="Mufli",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name=None,
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                notes="OpenRouter availability unknown.",
            ),
            ProviderRoute(
                provider="local_or_hosted",
                model_name="sea-lion",
                api_style="openai_compatible_or_transformers",
                notes="Non-OpenRouter placeholder route.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="Mistral Large 3",
        owner_name="Ana",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="mistralai/mistral-large-2512",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="mistral_direct",
                model_name="mistral-large-3",
                api_style="openai_compatible_or_mistral_chat",
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="Qwen3.5-27B",
        owner_name="Ana",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="qwen/qwen3.5-27b",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="local_or_hosted",
                model_name="qwen3.5-27b",
                api_style="openai_compatible_or_transformers",
                notes="Non-OpenRouter placeholder route.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="Olmo-3-32B-Think",
        owner_name="Ana",
        reasoning_mode="high",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="allenai/olmo-3-32b-think",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_reasoning_param=True,
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="local_or_hosted",
                model_name="olmo-3-32b-think",
                api_style="openai_compatible_or_transformers",
                notes="Non-OpenRouter placeholder route.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="Claude Sonnet",
        owner_name="Ram",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="anthropic/claude-sonnet-latest",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="anthropic_direct",
                model_name="claude-sonnet-latest",
                api_style="messages",
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="Claude Haiku",
        owner_name="Ram",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="anthropic/claude-haiku-latest",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="anthropic_direct",
                model_name="claude-haiku-latest",
                api_style="messages",
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="Grok 4.3",
        owner_name="Ram",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="x-ai/grok-4.3",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="xai_direct",
                model_name="grok-4.3",
                api_style="openai_compatible_or_xai",
                supports_json_schema=True,
                notes="Direct API placeholder.",
            ),
        ),
    ),
    JudgeModelSpec(
        alias="Qwen 3.7 Max",
        owner_name="Ram",
        routes=(
            ProviderRoute(
                provider="openrouter",
                model_name="qwen/qwen3.7-max",
                base_url=OPENROUTER_CHAT_COMPLETIONS_URL,
                api_style="openai_chat_completions",
                supports_search_toggle=True,
                supports_json_schema=True,
            ),
            ProviderRoute(
                provider="local_or_hosted",
                model_name="qwen3.7-max",
                api_style="openai_compatible_or_transformers",
                supports_search_toggle=True,
                notes="Non-OpenRouter placeholder route.",
            ),
        ),
    ),
)


def normalize_judge_instance(
    row: Mapping[str, Any],
    *,
    culture: str | None = None,
    row_index: int | None = None,
) -> dict[str, Any]:
    """Normalize either a pilot-dataset row or a raw spreadsheet row."""

    if "riddle_id" in row:
        missing = [field_name for field_name in JUDGE_REQUIRED_FIELDS if not _clean_string(row.get(field_name))]
        if missing:
            raise ValueError(f"Pilot row is missing judge-required fields: {missing}")
        return {
            "riddle_id": _clean_string(row.get("riddle_id")),
            "community": _clean_string(row.get("community")),
            "row_number": row.get("source_row_number"),
            "row_index": row_index,
            "topic": _clean_string(row.get("topic")),
            "language": _clean_string(row.get("language")),
            "language_secondary": _clean_string(row.get("language_secondary")),
            "riddle_original": _clean_string(row.get("riddle_original")),
            "riddle_english": _clean_string(row.get("riddle_english")),
            "hint": _clean_string(row.get("riddle_hint")),
            "comments": _clean_string(row.get("riddle_note")),
            "reference_answer_original": _clean_string(row.get("reference_answer_original")),
            "reference_answer_english": _clean_string(row.get("reference_answer_english")),
            "author": _clean_string(row.get("author_credit")),
            "human_validator_name": _clean_string(row.get("human_validator_name")),
            "human_answer_original": _clean_string(row.get("human_answer_original")),
            "human_answer_score": row.get("human_answer_score"),
            "human_answer_comment": _clean_string(row.get("human_answer_comment")),
        }

    number = row.get("Number")
    topic = _clean_string(row.get("Topic"))
    riddle_original = _clean_string(row.get("Riddle (Original Language)"))
    answer_original = _clean_string(row.get("Reference Answer (Original)"))
    community = culture or "unknown_community"

    if not number or not topic or not riddle_original or not answer_original:
        missing = [
            column
            for column in (
                "Number",
                "Topic",
                "Riddle (Original Language)",
                "Reference Answer (Original)",
            )
            if not _clean_string(row.get(column))
        ]
        raise ValueError(f"Spreadsheet row is missing judge-required fields: {missing}")

    riddle_id = f"{community.lower()}_{topic.lower().replace(' ', '_')}_{int(float(number)):03d}"
    return {
        "riddle_id": riddle_id,
        "community": community,
        "row_number": int(float(number)),
        "row_index": row_index,
        "topic": topic,
        "language": None,
        "language_secondary": None,
        "riddle_original": riddle_original,
        "riddle_english": _clean_string(row.get("Riddle (English Translation)")),
        "hint": _clean_string(row.get("Hints (Optional)")),
        "comments": _clean_string(
            row.get("Comments (Optional), e.g. about region/generation-specificity")
        ),
        "reference_answer_original": answer_original,
        "reference_answer_english": _clean_string(row.get("Reference Answer (English)")),
        "author": _clean_string(row.get("Author")),
        "human_validator_name": _clean_string(row.get("Human Validator Name")),
        "human_answer_original": _clean_string(row.get("Human Answer (Original)")),
        "human_answer_score": row.get("Rating of Human Answer (0-2)"),
        "human_answer_comment": _clean_string(
            row.get("Comment (Optional) about evaluation of human answer")
        ),
    }


def build_judge_messages(
    instance: Mapping[str, Any],
    *,
    candidate_answer: str,
) -> list[dict[str, str]]:
    """Build a minimal provider-agnostic judge prompt."""

    user_prompt = (
        "RIDDLE:\n"
        f"{instance['riddle_original']}\n\n"
        "HINT:\n"
        f"{instance.get('hint') or '(none)'}\n\n"
        "REFERENCE ANSWER:\n"
        f"{instance['reference_answer_original']}\n\n"
        "CANDIDATE ANSWER:\n"
        f"{candidate_answer}\n\n"
        "Evaluate whether the candidate answer is correct."
    )
    return [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_openrouter_payload(
    model_spec: JudgeModelSpec,
    messages: list[dict[str, str]],
    *,
    temperature: float | None = None,
    max_output_tokens: int = 512,
) -> dict[str, Any]:
    """Build an OpenRouter payload for a model that has an OpenRouter route."""

    route = select_route(model_spec, "openrouter")
    if route is None or not route.model_name:
        raise ValueError(f"No usable OpenRouter route for alias '{model_spec.alias}'.")

    payload: dict[str, Any] = {
        "model": route.model_name,
        "messages": messages,
        "temperature": model_spec.temperature_default if temperature is None else temperature,
        "max_tokens": max_output_tokens,
    }

    if route.supports_json_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "judge_result",
                "strict": True,
                "schema": JUDGE_OUTPUT_SCHEMA,
            },
        }

    if route.supports_reasoning_param and model_spec.reasoning_mode and model_spec.reasoning_mode != "none":
        payload["reasoning"] = {"effort": model_spec.reasoning_mode}

    return payload


def select_route(model_spec: JudgeModelSpec, provider: str) -> ProviderRoute | None:
    for route in model_spec.routes:
        if route.provider == provider:
            return route
    return None


def models_by_alias() -> dict[str, JudgeModelSpec]:
    return {model.alias: model for model in TARGET_MODELS}


def export_model_registry() -> list[dict[str, Any]]:
    return [asdict(model) for model in TARGET_MODELS]


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if value != value:
        return None
    return str(value).strip() or None
