from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.tools import Tool, StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from llm.llm_provider import get_llm
from tools.tool_registry import get_tools_for_agent
from agents.prompt_generator import generate_prompt
from utils.logger import get_logger

logger = get_logger(__name__)


def _wrap_tools(tool_funcs: dict) -> list:
    """Wrap plain Python functions into LangChain Tool objects.

    Uses StructuredTool so multi-argument functions (e.g. search_flights)
    receive proper keyword arguments from the LLM via the auto-generated
    JSON schema, instead of a single concatenated string.
    """
    lc_tools = []
    for name, func in tool_funcs.items():
        try:
            lc_tools.append(
                StructuredTool.from_function(
                    func=func,
                    name=name,
                    description=func.__doc__ or f"Tool: {name}",
                )
            )
        except Exception:
            # Fallback to plain Tool for functions that can't be introspected
            lc_tools.append(
                Tool(
                    name=name,
                    func=func,
                    description=func.__doc__ or f"Tool: {name}",
                )
            )
    return lc_tools


def build_agent(agent_def):
    """
    Build the appropriate executor from an AgentDefinition.

    Returns:
      - dict {"type": "deterministic", "tools": ...}  for deterministic agents
      - AgentExecutor   for reasoning / hybrid agents
      - None            for data_collector / aggregator (executor not needed;
                        agent_executor.py handles them directly via LLM chains)
    """
    agent_type = agent_def.agent_type
    behavior   = getattr(agent_def, "behavior", "task_executor")

    logger.info(
        {"event": "build_agent", "name": agent_def.name,
         "type": agent_type, "behavior": behavior}
    )

    # ── Deterministic: direct tool call, no LLM ──────────────────────────────
    if agent_type == "deterministic":
        tool_funcs = get_tools_for_agent(agent_def.tools)
        if not tool_funcs:
            raise ValueError(
                f"Deterministic agent '{agent_def.name}' must have at least one tool assigned."
            )
        logger.info({"event": "build_agent_deterministic", "name": agent_def.name,
                     "tools": list(tool_funcs.keys())})
        return {"type": "deterministic", "tools": tool_funcs, "agent_def": agent_def}

    # ── data_collector / aggregator: handled entirely in agent_executor ───────
    # They use llm.with_structured_output() directly — no AgentExecutor needed.
    if behavior in ("data_collector", "aggregator"):
        logger.info({"event": "build_agent_skip_executor", "name": agent_def.name,
                     "reason": f"behavior={behavior} uses direct LLM chain"})
        return None   # agent_executor.py will build the chain itself

    # ── Reasoning / Hybrid: LangChain AgentExecutor with tool-calling loop ────
    if not agent_def.llm_model:
        raise ValueError(
            f"Agent '{agent_def.name}' of type '{agent_type}' requires an LLM model."
        )

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
        agent=agent,
        tools=lc_tools,
        verbose=True,
        max_iterations=8,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
    )
    logger.info({"event": "build_agent_executor", "name": agent_def.name,
                 "model": agent_def.llm_model, "tools": [t.name for t in lc_tools]})
    return executor




