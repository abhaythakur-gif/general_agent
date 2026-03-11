from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from llm.llm_provider import get_llm
from tools.tool_registry import get_tools_for_agent
from agents.prompt_generator import generate_prompt
from utils.logger import get_logger

logger = get_logger(__name__)


def _wrap_tools(tool_funcs: dict) -> list:
    """Wrap plain Python functions into LangChain Tool objects."""
    lc_tools = []
    for name, func in tool_funcs.items():
        lc_tools.append(
            Tool(
                name=name,
                func=func,
                description=func.__doc__ or f"Tool: {name}",
            )
        )
    return lc_tools


def build_agent(agent_def) -> AgentExecutor:
    """
    Build a LangChain AgentExecutor from an AgentDefinition.
    Handles all three agent types: deterministic, reasoning, hybrid.
    """
    agent_type = agent_def.agent_type
    system_prompt = generate_prompt(agent_def)

    # --- Deterministic: no LLM, single tool call ---
    if agent_type == "deterministic":
        tool_funcs = get_tools_for_agent(agent_def.tools)
        if not tool_funcs:
            raise ValueError(
                f"Deterministic agent '{agent_def.name}' must have at least one tool assigned."
            )
        # Return None here; the executor handles these directly
        logger.get_logger(__name__) if False else None
        return {"type": "deterministic", "tools": tool_funcs, "agent_def": agent_def}

    # --- Reasoning / Hybrid: LLM + tools via OpenAI Tools agent ---
    if not agent_def.llm_model:
        raise ValueError(
            f"Agent '{agent_def.name}' of type '{agent_type}' requires an LLM model."
        )

    llm = get_llm(agent_def.llm_model)
    tool_funcs = get_tools_for_agent(agent_def.tools)
    lc_tools = _wrap_tools(tool_funcs)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm=llm, tools=lc_tools, prompt=prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=lc_tools,
        verbose=True,
        max_iterations=8,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
    )
    return executor




