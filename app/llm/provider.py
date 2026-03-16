from langchain_openai import ChatOpenAI
from app.core.config import settings

SUPPORTED_MODELS = {
    "gpt-4":         {"model": "gpt-4",         "temperature": 0.7},
    "gpt-4-turbo":   {"model": "gpt-4-turbo",   "temperature": 0.7},
    "gpt-3.5-turbo": {"model": "gpt-3.5-turbo", "temperature": 0.7},
}


def get_llm(model_name: str = "gpt-4") -> ChatOpenAI:
    """Return a configured LangChain ChatOpenAI instance."""
    if model_name not in SUPPORTED_MODELS:
        raise ValueError(
            f"Model '{model_name}' is not supported. "
            f"Supported: {list(SUPPORTED_MODELS.keys())}"
        )
    config = SUPPORTED_MODELS[model_name]
    return ChatOpenAI(
        model=config["model"],
        temperature=config["temperature"],
        api_key=settings.OPENAI_API_KEY,
    )


def list_models() -> list:
    return list(SUPPORTED_MODELS.keys())
