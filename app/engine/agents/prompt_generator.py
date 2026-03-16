from app.tools.registry import tool_metadata


def _field_label(f) -> str:
    req = "REQUIRED" if f.required else "optional"
    desc = f" — {f.description}" if f.description else ""
    return f"  • {f.name} ({f.type}, {req}){desc}"


def _prompt_task_executor(agent_def) -> str:
    tool_lines = []
    for tool_name in agent_def.tools:
        meta = tool_metadata.get(tool_name, {})
        desc = meta.get("description", "No description available.")
        inputs_list = ", ".join(meta.get("inputs", []))
        tool_lines.append(f"  • {tool_name}({inputs_list}): {desc}")
    tools_section = "\n".join(tool_lines) if tool_lines else "  None"

    if agent_def.input_schema:
        inp_section = "\n".join(_field_label(f) for f in agent_def.input_schema)
    else:
        inp_section = "  " + ", ".join(agent_def.inputs) if agent_def.inputs else "  None"

    if agent_def.output_schema:
        out_section = "\n".join(_field_label(f) for f in agent_def.output_schema)
    else:
        out_section = "\n".join(f"  • {o}" for o in agent_def.outputs) if agent_def.outputs else "  None"

    behavior_note = (
        "\nYou are aggregating results from multiple upstream agents. "
        "Combine all inputs into a coherent, complete output.\n"
    ) if getattr(agent_def, "behavior", "task_executor") == "aggregator" else ""

    return f"""You are an AI agent with the following role:
{agent_def.description}
{behavior_note}
INPUT VARIABLES (available in workflow state):
{inp_section}

AVAILABLE TOOLS:
{tools_section}

OUTPUT VARIABLES you must produce:
{out_section}

Instructions:
- Use the tools listed above — do not invent or call any other tool.
- Structure your final answer so every output variable is clearly present with its exact name.
- Be thorough, accurate, and concise.
""".strip()


def _prompt_data_collector(agent_def, already_collected: dict | None = None) -> str:
    if agent_def.output_schema:
        field_lines = "\n".join(_field_label(f) for f in agent_def.output_schema)
    else:
        field_lines = "\n".join(f"  • {o} (str, REQUIRED)" for o in agent_def.outputs)

    collected_section = ""
    if already_collected:
        collected_lines = "\n".join(
            f"  • {k}: {v}" for k, v in already_collected.items() if v is not None
        )
        collected_section = f"\nALREADY COLLECTED (from previous messages):\n{collected_lines}\n"

    return f"""You are a data-collection agent. Your job is to extract structured information
from the user's message and determine whether all required fields have been provided.

AGENT ROLE: {agent_def.description}

FIELDS TO COLLECT:
{field_lines}
{collected_section}
INSTRUCTIONS:
1. Extract every field you can from the user's current message AND the already-collected data above.
2. Set `collection_status` to "complete" if ALL REQUIRED fields now have values, otherwise "incomplete".
3. If "incomplete", set `follow_up_question` to a single, friendly, conversational question
   asking ONLY for the missing REQUIRED fields.
4. List any still-missing REQUIRED field names in `missing_fields`.
5. Return your response as valid JSON matching the output schema exactly.
   Use null for optional fields that were not provided.
""".strip()


def generate_prompt(agent_def, already_collected: dict | None = None) -> str:
    behavior = getattr(agent_def, "behavior", "task_executor")
    if behavior == "data_collector":
        return _prompt_data_collector(agent_def, already_collected)
    return _prompt_task_executor(agent_def)
