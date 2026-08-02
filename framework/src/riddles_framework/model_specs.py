"""Model spec scaffolds.

NOTE: The model IDs and provider_model_name strings below are placeholders
intended for the v1 framework scaffolding. Before any production benchmark
run, replace these with the actual provider model strings the team has
confirmed access to.
"""

from __future__ import annotations

from .schemas import ModelCapabilities, ModelSpec


def dummy_spec() -> ModelSpec:
    return ModelSpec(
        model_name="Dummy Echo",
        model_id="dummy/echo-v1",
        provider="dummy",
        access_pattern="local",
        provider_model_name="dummy-echo-v1",
        capabilities=ModelCapabilities(
            supports_reasoning=False,
            supports_search=False,
            supports_structured_output=True,
            supports_batch=False,
            supports_seed=False,
        ),
        closed_source=False,
        notes="Dummy test model",
    )


def openai_gpt55_high_spec() -> ModelSpec:
    return ModelSpec(
        model_name="GPT5.5-high",
        model_id="openai/gpt-5.5-high",
        provider="openai",
        access_pattern="direct_api",
        provider_model_name="gpt-5.5-high",
        capabilities=ModelCapabilities(
            supports_reasoning=True,
            supports_search=False,
            supports_structured_output=True,
            supports_batch=False,
            supports_seed=True,
        ),
        closed_source=True,
        notes="OpenAI reasoning-heavy model",
    )


def openai_gpt55_none_spec() -> ModelSpec:
    return ModelSpec(
        model_name="GPT5.5-none",
        model_id="openai/gpt-5.5-none",
        provider="openai",
        access_pattern="direct_api",
        provider_model_name="gpt-5.5-none",
        capabilities=ModelCapabilities(
            supports_reasoning=False,
            supports_search=False,
            supports_structured_output=True,
            supports_batch=False,
            supports_seed=True,
        ),
        closed_source=True,
        notes="OpenAI non-reasoning variant",
    )


def anthropic_claude_opus_thinking_spec() -> ModelSpec:
    return ModelSpec(
        model_name="claude-opus-4-7-thinking",
        model_id="anthropic/claude-opus-4.7-thinking",
        provider="anthropic",
        access_pattern="direct_api",
        provider_model_name="claude-opus-4-7-thinking",
        capabilities=ModelCapabilities(
            supports_reasoning=True,
            supports_search=False,
            supports_structured_output=False,
            supports_batch=False,
            supports_seed=False,
        ),
        closed_source=True,
        notes="Anthropic extended thinking variant",
    )


def anthropic_claude_opus_spec() -> ModelSpec:
    return ModelSpec(
        model_name="claude-opus-4-7",
        model_id="anthropic/claude-opus-4.7",
        provider="anthropic",
        access_pattern="direct_api",
        provider_model_name="claude-opus-4-7",
        capabilities=ModelCapabilities(
            supports_reasoning=False,
            supports_search=False,
            supports_structured_output=False,
            supports_batch=False,
            supports_seed=False,
        ),
        closed_source=True,
        notes="Anthropic standard variant",
    )


def gemini_pro_preview_spec() -> ModelSpec:
    return ModelSpec(
        model_name="gemini-3.1-pro-preview",
        model_id="google/gemini-3.1-pro-preview",
        provider="google",
        access_pattern="direct_api",
        provider_model_name="gemini-3.1-pro-preview",
        capabilities=ModelCapabilities(
            supports_reasoning=True,
            supports_search=False,
            supports_structured_output=False,
            supports_batch=False,
            supports_seed=False,
        ),
        closed_source=True,
        notes="Gemini Pro preview",
    )


def openrouter_qwen37max_spec() -> ModelSpec:
    return ModelSpec(
        model_name="Qwen 3.7 Max",
        model_id="qwen/qwen-3.7-max-openrouter",
        provider="qwen",
        access_pattern="openrouter",
        provider_model_name="qwen/qwen3-7-max",
        capabilities=ModelCapabilities(
            supports_reasoning=True,
            supports_search=True,
            supports_structured_output=True,
            supports_batch=False,
            supports_seed=False,
        ),
        closed_source=True,
        notes="Qwen via OpenRouter",
    )


def together_llama_33_70b_spec() -> ModelSpec:
    return ModelSpec(
        model_name="Llama 3.3 70B Instruct Turbo",
        model_id="together/llama-3.3-70b-instruct-turbo",
        provider="together",
        access_pattern="together",
        provider_model_name="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        capabilities=ModelCapabilities(
            supports_reasoning=False,
            supports_search=False,
            supports_structured_output=True,
            supports_batch=False,
            supports_seed=False,
        ),
        closed_source=False,
        notes="Llama via Together",
    )


def together_deepseek_v4_pro_spec() -> ModelSpec:
    return ModelSpec(
        model_name="DeepSeek V4 Pro",
        model_id="together/deepseek-v4-pro",
        provider="together",
        access_pattern="together",
        provider_model_name="deepseek-ai/DeepSeek-V4-Pro",
        capabilities=ModelCapabilities(
            supports_reasoning=True,
            supports_search=False,
            supports_structured_output=True,
            supports_batch=False,
            supports_seed=False,
        ),
        closed_source=False,
        notes="DeepSeek via Together",
    )


def cohere_command_a_spec() -> ModelSpec:
    return ModelSpec(
        model_name="Command A",
        model_id="cohere/command-a-03-2025",
        provider="cohere",
        access_pattern="direct_api",
        provider_model_name="command-a-03-2025",
        capabilities=ModelCapabilities(
            supports_reasoning=False,
            supports_search=False,
            supports_structured_output=True,
            supports_batch=False,
            supports_seed=True,
        ),
        closed_source=True,
        notes="Cohere Command A via direct API",
    )


def local_transformers_spec(model_name: str) -> ModelSpec:
    return ModelSpec(
        model_name=model_name,
        model_id=f"local/{model_name.replace('/', '__')}",
        provider="local",
        access_pattern="local",
        provider_model_name=model_name,
        capabilities=ModelCapabilities(
            supports_reasoning=False,
            supports_search=False,
            supports_structured_output=False,
            supports_batch=True,
            supports_seed=True,
        ),
        closed_source=False,
        notes="Local transformers model",
    )
