"""
app/services/llm/providers/openai.py
--------------------------------------
OpenAI / ChatOpenAI provider.
Replaces the old app/llm/provider.py.

To add another provider (e.g. Anthropic):
  1. Create app/services/llm/providers/anthropic.py
  2. Register it in registry.py
"""

from langchain_openai import ChatOpenAI

from app.config.settings import settings
from app.services.llm.base.base_client import BaseLLMClient

SUPPORTED_MODELS: dict = {
    "gpt-4":         {"model": "gpt-4",         "temperature": 0.7},
    "gpt-4-turbo":   {"model": "gpt-4-turbo",   "temperature": 0.7},
    "gpt-3.5-turbo": {"model": "gpt-3.5-turbo", "temperature": 0.7},
}


class OpenAIClient(BaseLLMClient):

    def get_chat_model(self, model_name: str = "gpt-4") -> ChatOpenAI:
        if model_name not in SUPPORTED_MODELS:
            raise ValueError(
                f"Model '{model_name}' is not supported by the OpenAI provider. "
                f"Supported: {list(SUPPORTED_MODELS.keys())}"
            )
        cfg = SUPPORTED_MODELS[model_name]
        return ChatOpenAI(
            model=cfg["model"],
            temperature=cfg["temperature"],
            api_key=settings.OPENAI_API_KEY,
        )

    def list_models(self) -> list:
        return list(SUPPORTED_MODELS.keys())


# ── Module-level convenience helpers (drop-in replacements for old provider.py) ─

_client = OpenAIClient()


def get_llm(model_name: str = "gpt-4") -> ChatOpenAI:
    """Return a configured LangChain ChatOpenAI instance."""
    return _client.get_chat_model(model_name)


def list_models() -> list:
    """Return all supported LLM model names."""
    return _client.list_models()
