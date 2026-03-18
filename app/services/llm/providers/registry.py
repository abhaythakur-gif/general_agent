"""
app/services/llm/providers/registry.py
-----------------------------------------
Maps provider/model name strings → provider class instances.
Enables runtime provider switching via config without code changes.
"""

from app.services.llm.providers.openai import OpenAIClient, get_llm, list_models  # noqa: F401

# Provider registry: add new providers here without changing callers
_PROVIDER_MAP: dict = {
    "openai": OpenAIClient(),
}

# Model-name prefix → provider routing (extend when adding more providers)
_MODEL_PREFIX_TO_PROVIDER: dict = {
    "gpt-": "openai",
}


def get_provider_for_model(model_name: str):
    """Return the correct provider instance for a given model name."""
    for prefix, provider_key in _MODEL_PREFIX_TO_PROVIDER.items():
        if model_name.startswith(prefix):
            return _PROVIDER_MAP[provider_key]
    # Default fallback
    return _PROVIDER_MAP["openai"]
