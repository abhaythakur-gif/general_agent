"""
app/services/llm/base/base_client.py
--------------------------------------
Abstract base class for every LLM provider.
Add a new provider by extending BaseLLMClient and registering it in registry.py.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMClient(ABC):
    """Minimal interface every concrete LLM provider must implement."""

    @abstractmethod
    def get_chat_model(self, model_name: str) -> Any:
        """Return a LangChain-compatible chat model for the given model name."""

    @abstractmethod
    def list_models(self) -> list:
        """Return the list of model names supported by this provider."""
