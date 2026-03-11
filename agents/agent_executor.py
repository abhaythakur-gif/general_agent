import time
from agents.agent_factory import build_agent
from utils.logger import get_logger

logger = get_logger(__name__)


def run_agent(agent_def, workflow_state: dict, log_callback=None) -> dict:
    """
    Execute a single agent within the workflow.

    - Extracts the agent's required inputs from workflow_state
    - Runs the agent (deterministic or LLM-based)
    - Maps outputs back into a dict to merge into workflow_state
    - Returns the dict of new state variables produced

    log_callback: optional callable(event_dict) for real-time log streaming
    """
    def log(event: str, **kwargs):
        entry = {"event": event, "agent": agent_def.name, "timestamp": time.time(), **kwargs}
        logger.info(entry)
        if log_callback:
            log_callback(entry)

    log("agent_start")
    start = time.time()

    # Extract inputs from current state
    input_values = {k: workflow_state.get(k, "") for k in agent_def.inputs}

    try:
        built = build_agent(agent_def)

        # --- Deterministic agent ---
        if isinstance(built, dict) and built.get("type") == "deterministic":
            tool_funcs = built["tools"]
            tool_name = agent_def.tools[0]
            tool_fn = tool_funcs.get(tool_name)
            if not tool_fn:
                raise ValueError(f"Tool '{tool_name}' not found in registry.")

            # Pass input values positionally (first input value as the main arg)
            first_input = list(input_values.values())[0] if input_values else ""
            log("tool_call", tool=tool_name, input=first_input)
            result = tool_fn(first_input)
            log("tool_response", tool=tool_name, output=str(result)[:300])

            output_updates = {}
            for out_var in agent_def.outputs:
                output_updates[out_var] = result
            duration_ms = round((time.time() - start) * 1000)
            log("agent_complete", duration_ms=duration_ms)
            return output_updates

        # --- Reasoning / Hybrid agent ---
        # Build the input string from all input variables
        input_text = "\n".join([f"{k}: {v}" for k, v in input_values.items()])
        if not input_text:
            input_text = "Begin your task."

        log("llm_start", model=agent_def.llm_model, input_preview=input_text[:200])
        result = built.invoke({"input": input_text})
        output_text = result.get("output", "")
        log("llm_complete", output_preview=output_text[:300])

        # Map the LLM output string to each declared output variable
        # Use the full output under all declared output names
        output_updates = {}
        if len(agent_def.outputs) == 1:
            output_updates[agent_def.outputs[0]] = output_text
        else:
            # Attempt to parse sections if multiple outputs declared
            for out_var in agent_def.outputs:
                # Look for patterns like "variable_name:" in the response
                lines = output_text.split("\n")
                section = []
                in_section = False
                for line in lines:
                    if line.lower().startswith(out_var.lower() + ":"):
                        in_section = True
                        section.append(line.split(":", 1)[-1].strip())
                    elif in_section and line.strip():
                        section.append(line)
                    elif in_section and not line.strip():
                        break
                output_updates[out_var] = "\n".join(section) if section else output_text

        duration_ms = round((time.time() - start) * 1000)
        log("agent_complete", duration_ms=duration_ms)
        return output_updates

    except Exception as e:
        log("agent_error", error=str(e))
        raise RuntimeError(f"Agent '{agent_def.name}' failed: {str(e)}") from e
