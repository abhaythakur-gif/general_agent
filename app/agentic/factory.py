"""
app/agentic/factory.py
-----------------------
Builds (instantiates) the correct agent executor given an AgentDefinition.
Replaces app/engine/agents/factory.py.
"""

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.tools import Tool, StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.services.llm.providers.openai import get_llm
from app.utils.tools.registry import get_tools_for_agent
from app.agentic.agents.reasoning.prompts import generate_prompt
from app.config.logging import get_logger

logger = get_logger(__name__)


def _wrap_tools(tool_funcs: dict) -> list:
    lc_tools = []
    for name, func in tool_funcs.items():
        try:
            lc_tools.append(StructuredTool.from_function(
                func=func, name=name, description=func.__doc__ or f"Tool: {name}",
            ))
        except Exception:
            lc_tools.append(Tool(name=name, func=func, description=func.__doc__ or f"Tool: {name}"))
    return lc_tools


def build_agent(agent_def):
    agent_type = agent_def.agent_type
    behavior   = getattr(agent_def, "behavior", "task_executor")

    logger.info({"event": "build_agent", "name": agent_def.name, "type": agent_type, "behavior": behavior})

    if agent_type == "deterministic":
        tool_funcs = get_tools_for_agent(agent_def.tools)
        if not tool_funcs:
            raise ValueError(f"Deterministic agent '{agent_def.name}' must have at least one tool assigned.")
        return {"type": "deterministic", "tools": tool_funcs, "agent_def": agent_def}

    if behavior in ("data_collector", "aggregator"):
        return None

    if not agent_def.llm_model:
        raise ValueError(f"Agent '{agent_def.name}' of type '{agent_type}' requires an LLM model.")

    llm        = get_llm(agent_def.llm_model)
    tool_funcs = get_tools_for_agent(agent_def.tools)
    lc_tools   = _wrap_tools(tool_funcs)
    system_prompt = generate_prompt(agent_def)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm=llm, tools=lc_tools, prompt=prompt)
    executor = AgentExecutor(
        agent=agent, tools=lc_tools, verbose=True,
        max_iterations=8, return_intermediate_steps=True, handle_parsing_errors=True,
    )
    logger.info({"event": "build_agent_executor", "name": agent_def.name,
                 "model": agent_def.llm_model, "tools": [t.name for t in lc_tools]})
    return executor
