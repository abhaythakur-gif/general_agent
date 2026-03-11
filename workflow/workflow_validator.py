from tools.tool_registry import tool_registry


def validate_workflow(agent_defs: list) -> list:
    """
    Validate a sequence of agent definitions before execution.
    Returns a list of error strings. Empty list means valid.
    """
    errors = []
    available_vars = set()

    for idx, agent in enumerate(agent_defs):
        position = idx + 1

        # Check tools exist in registry
        for tool_name in agent.tools:
            if tool_name not in tool_registry:
                errors.append(
                    f"Agent {position} ('{agent.name}'): tool '{tool_name}' is not registered."
                )

        # Check all required inputs are available in state
        for inp in agent.inputs:
            if inp not in available_vars:
                if idx == 0:
                    # First agent inputs must come from user — warn but allow
                    pass
                else:
                    errors.append(
                        f"Agent {position} ('{agent.name}'): requires input '{inp}' "
                        f"but no previous agent produces it. "
                        f"Available variables: {sorted(available_vars)}"
                    )

        # After validation, add this agent's outputs to available vars
        for out in agent.outputs:
            available_vars.add(out)

    return errors

