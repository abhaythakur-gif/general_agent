"""
app/engine/agents/executor.py
------------------------------
Executes a single AgentDefinition against the current workflow state.
"""
import time
import threading
from typing import Any, Dict, Optional

from pydantic import create_model
from langchain_core.messages import SystemMessage, HumanMessage

from app.engine.agents.factory import build_agent
from app.engine.agents.prompt_generator import generate_prompt, _prompt_data_collector
from app.core.logger import get_logger

logger = get_logger(__name__)

_TYPE_MAP: Dict[str, type] = {
    "str": str, "int": int, "float": float, "bool": bool, "list": list, "dict": dict,
}

_LOG_LOCK = threading.Lock()


def _build_output_model(output_schema: list, model_name: str = "AgentOutput"):
    from typing import Any as AnyT, Optional as Opt, Literal
    fields: Dict[str, Any] = {}
    for f in output_schema:
        allowed = getattr(f, "allowed_values", None)
        if allowed and len(allowed) >= 1 and f.type in ("str", "int", "bool"):
            normalised = (
                [v.strip().lower() for v in allowed] if f.type == "str"
                else [v.strip() for v in allowed]
            )
            literal_type = Literal[tuple(normalised)]  # type: ignore[valid-type]
            fields[f.name] = (literal_type, ...) if f.required else (Opt[literal_type], f.default)  # type: ignore
        else:
            fields[f.name] = (AnyT, ...) if f.required else (Opt[AnyT], f.default)
    return create_model(model_name, **fields)


def _build_data_collector_model(output_schema: list):
    from typing import Any as AnyT, Optional as Opt, List as Lst
    fields: Dict[str, Any] = {}
    for f in output_schema:
        fields[f.name] = (Opt[AnyT], None)
    fields["collection_status"]  = (str, ...)
    fields["follow_up_question"] = (Opt[str], None)
    fields["missing_fields"]     = (Opt[Lst[str]], None)
    return create_model("DataCollectorOutput", **fields)


def _coerce_to_schema(result_dict: dict, output_schema: list) -> dict:
    import json
    coerced = dict(result_dict)
    for f in output_schema:
        val = coerced.get(f.name)
        if val is None:
            continue
        target = f.type
        try:
            if target == "str" and not isinstance(val, str):
                coerced[f.name] = json.dumps(val, ensure_ascii=False) if isinstance(val, (list, dict)) else str(val)
            elif target == "int" and not isinstance(val, int):
                coerced[f.name] = int(float(str(val).replace(",", "")))
            elif target == "float" and not isinstance(val, float):
                coerced[f.name] = float(str(val).replace(",", ""))
            elif target == "bool" and not isinstance(val, bool):
                coerced[f.name] = str(val).lower() in ("true", "1", "yes")
            elif target == "list" and not isinstance(val, list):
                coerced[f.name] = json.loads(val) if isinstance(val, str) else list(val)
            elif target == "dict" and not isinstance(val, dict):
                coerced[f.name] = json.loads(val) if isinstance(val, str) else dict(val)
        except Exception:
            pass
    return coerced


def _run_deterministic(agent_def, input_values: dict, built: dict, log) -> dict:
    tool_funcs = built["tools"]
    tool_name  = agent_def.tools[0]
    tool_fn    = tool_funcs.get(tool_name)
    if not tool_fn:
        raise ValueError(f"Tool '{tool_name}' not found in registry.")
    log("tool_call", tool=tool_name, input=str(input_values)[:200])
    try:
        result = tool_fn(**input_values)
    except TypeError:
        result = tool_fn(*list(input_values.values()))
    log("tool_response", tool=tool_name, output=str(result)[:300])
    return {out_var: result for out_var in agent_def.effective_outputs}


def _run_data_collector(agent_def, input_values: dict, workflow_state: dict, llm, log) -> dict:
    output_schema = agent_def.output_schema
    if not output_schema:
        raise ValueError(f"data_collector agent '{agent_def.name}' must have an output_schema defined.")

    # ── Short-circuit: if all required output fields are already in workflow
    #    state (pre-filled by the Smart Router), skip the LLM call entirely.
    required_names = [f.name for f in output_schema if f.required]
    already_in_state = {
        f.name: workflow_state.get(f.name)
        for f in output_schema
        if workflow_state.get(f.name) is not None
    }
    truly_missing_upfront = [n for n in required_names if already_in_state.get(n) is None]

    if not truly_missing_upfront:
        # All required fields already present — return complete immediately, no LLM needed.
        result = {f.name: already_in_state.get(f.name) for f in output_schema}
        result["collection_status"]  = "complete"
        result["follow_up_question"] = None
        result["missing_fields"]     = []
        return result

    # ── Normal path: invoke LLM to extract/collect missing fields ────────────
    already_collected = already_in_state or None
    system_prompt = _prompt_data_collector(agent_def, already_collected)
    output_model  = _build_data_collector_model(output_schema)
    structured_llm = llm.with_structured_output(output_model)

    user_message = (
        input_values.get("user_message")
        or workflow_state.get("user_message", "")
        or " ".join(str(v) for v in input_values.values() if v)
    )
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
    result = structured_llm.invoke(messages)
    result_dict = result.model_dump()
    result_dict = _coerce_to_schema(result_dict, output_schema)

    truly_missing  = [n for n in required_names if result_dict.get(n) is None]

    if truly_missing:
        result_dict["collection_status"]  = "incomplete"
        result_dict["missing_fields"]     = truly_missing
        if not result_dict.get("follow_up_question"):
            result_dict["follow_up_question"] = f"Could you please provide: {', '.join(truly_missing)}?"
    else:
        result_dict["collection_status"]  = "complete"
        result_dict["follow_up_question"] = None
        result_dict["missing_fields"]     = []

    return result_dict


def _run_structured(agent_def, input_values: dict, agent_executor, llm, log) -> dict:
    output_schema = agent_def.output_schema
    input_text = "\n".join(f"{k}: {v}" for k, v in input_values.items()) or "Begin your task."
    result      = agent_executor.invoke({"input": input_text})
    output_text = result.get("output", "")

    if output_schema:
        try:
            output_model   = _build_output_model(output_schema, "TaskOutput")
            structured_llm = llm.with_structured_output(output_model)
            parsed = structured_llm.invoke(f"Extract fields from:\n{output_text}")
            return _coerce_to_schema(parsed.model_dump(), output_schema)
        except Exception:
            pass

    effective_outputs = agent_def.effective_outputs
    if len(effective_outputs) == 1:
        return {effective_outputs[0]: output_text}

    output_updates: Dict[str, Any] = {}
    found_any = False
    for out_var in effective_outputs:
        section, in_section = [], False
        for line in output_text.split("\n"):
            if line.lower().startswith(out_var.lower() + ":"):
                in_section = True
                section.append(line.split(":", 1)[-1].strip())
            elif in_section and line.strip():
                section.append(line)
            elif in_section and not line.strip():
                break
        if section:
            output_updates[out_var] = "\n".join(section)
            found_any = True
        else:
            output_updates[out_var] = ""
    if not found_any and effective_outputs:
        output_updates[effective_outputs[0]] = output_text
    return output_updates


def run_agent(agent_def, workflow_state: dict, log_callback=None) -> dict:
    def log(event: str, **kwargs):
        entry = {"event": event, "agent": agent_def.name, "timestamp": time.time(), **kwargs}
        with _LOG_LOCK:
            logger.info(entry)
            if log_callback:
                log_callback(entry)

    behavior = getattr(agent_def, "behavior", "task_executor")
    log("agent_start", agent_type=agent_def.agent_type, behavior=behavior,
        inputs=agent_def.effective_inputs, outputs=agent_def.effective_outputs)
    start = time.time()

    input_values = {k: workflow_state.get(k, "") for k in agent_def.effective_inputs}

    try:
        built = build_agent(agent_def)

        if isinstance(built, dict) and built.get("type") == "deterministic":
            output_updates = _run_deterministic(agent_def, input_values, built, log)

        elif behavior == "data_collector":
            from app.llm.provider import get_llm
            llm = get_llm(agent_def.llm_model)
            output_updates = _run_data_collector(agent_def, input_values, workflow_state, llm, log)

        elif behavior == "aggregator":
            from app.llm.provider import get_llm
            llm = get_llm(agent_def.llm_model)
            output_schema = agent_def.output_schema
            system_prompt = generate_prompt(agent_def)
            input_text    = "\n".join(f"{k}: {v}" for k, v in input_values.items())
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=input_text)]

            if output_schema:
                all_str_fields = all((f.type or "str") == "str" for f in output_schema)
                if all_str_fields:
                    result_text = llm.invoke(messages).content
                    output_updates = {f.name: result_text for f in output_schema}
                else:
                    output_model   = _build_output_model(output_schema, "AggregatorOutput")
                    structured_llm = llm.with_structured_output(output_model)
                    result = structured_llm.invoke(messages)
                    output_updates = _coerce_to_schema(result.model_dump(), output_schema)
            else:
                output_updates = _run_structured(agent_def, input_values, built, llm, log)

        else:
            from app.llm.provider import get_llm
            llm = get_llm(agent_def.llm_model)
            output_updates = _run_structured(agent_def, input_values, built, llm, log)

        log("agent_complete", duration_ms=round((time.time() - start) * 1000), behavior=behavior)
        return output_updates

    except Exception as e:
        log("agent_error", error=str(e))
        raise RuntimeError(f"Agent '{agent_def.name}' failed: {str(e)}") from e
