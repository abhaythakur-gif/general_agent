"""
app/config/llm/static.py
-------------------------
Python-side default values for the LLM configuration block.
Override any of these via environment variables or database config.
"""

from app.config.llm.models import LLMModelConfig

DEFAULT_LLM_CONFIGS: dict[str, LLMModelConfig] = {
    "gpt-4": LLMModelConfig(
        model="gpt-4",
        temperature=0.7,
        description="Most capable GPT-4 model, best quality for reasoning tasks.",
    ),
    "gpt-4-turbo": LLMModelConfig(
        model="gpt-4-turbo",
        temperature=0.7,
        description="Faster and cheaper GPT-4 variant with 128k context.",
    ),
    "gpt-3.5-turbo": LLMModelConfig(
        model="gpt-3.5-turbo",
        temperature=0.7,
        description="Fast and cost-effective model for simpler tasks.",
    ),
}

DEFAULT_MODEL = "gpt-4"
