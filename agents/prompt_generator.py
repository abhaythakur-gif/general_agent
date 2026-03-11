from tools.tool_registry import tool_metadata


def generate_prompt(agent_def) -> str:
    """
    Auto-generate a system prompt from an agent definition.
    Users only provide a description - this function builds the full prompt.
    """
    tool_lines = []
    for tool_name in agent_def.tools:
        meta = tool_metadata.get(tool_name, {})
        desc = meta.get("description", "No description available.")
        inputs_list = ", ".join(meta.get("inputs", []))
        tool_lines.append(f"  - {tool_name}({inputs_list}): {desc}")

    tools_section = "\n".join(tool_lines) if tool_lines else "  None"
    inputs_section = ", ".join(agent_def.inputs) if agent_def.inputs else "None"
    outputs_section = "\n".join([f"  - {o}" for o in agent_def.outputs]) if agent_def.outputs else "  None"

    prompt = f"""You are an AI agent with the following role:
{agent_def.description}

You will receive the following input variables from the workflow state:
{inputs_section}

You have access to the following tools:
{tools_section}

Your task:
Use your reasoning and the available tools to accomplish your role.
Produce the following output variables:
{outputs_section}

Important:
- Only use the tools listed above. Do not attempt to use any other tools.
- Structure your final response so each output variable is clearly present.
- Be thorough, accurate, and concise.
"""
    return prompt.strip()
