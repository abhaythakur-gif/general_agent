"""
app/controllers/tools/schema/response/tools_response.py
========================================================
Pydantic response schemas for the Tools & Models controller.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel


class ToolsListOut(BaseModel):
    """
    All tools available in the platform, both as a flat list and grouped
    by category.

    Returned by ``GET /tools``.

    ### Shape
    ```json
    {
      "tools": [
        {
          "name": "web_search",
          "category": "Search",
          "description": "Searches the web via SerpAPI",
          "parameters": ["query"]
        }
      ],
      "grouped": {
        "Search": [ { ...tool... } ],
        "Weather": [ { ...tool... } ]
      },
      "total": 8
    }
    ```
    """

    tools: List[Dict[str, Any]]
    grouped: Dict[str, List[Dict[str, Any]]]
    total: int


class ModelsListOut(BaseModel):
    """
    All supported LLM models.

    Returned by ``GET /models``.

    ### Shape
    ```json
    {
      "models": [
        { "id": "gpt-4", "provider": "openai", "description": "GPT-4" },
        { "id": "gpt-4o", "provider": "openai", "description": "GPT-4o" }
      ]
    }
    ```
    """

    models: List[Any]
