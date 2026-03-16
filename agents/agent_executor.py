"""
agent_executor.py
-----------------
Executes a single AgentDefinition against the current workflow state.

Dispatch logic:
  deterministic  → direct tool call, no LLM
  data_collector → LLM + with_structured_output; validates completeness; pauses if incomplete
  task_executor  → AgentExecutor (tool loop) + optional structured output on finish
  aggregator     → direct LLM chain + with_structured_output
"""
import time
import threading
from typing import Any, Dict, Optional

from pydantic import create_model
from langchain_core.messages import SystemMessage, HumanMessage

from agents.agent_factory import build_agent
from agents.prompt_generator import generate_prompt, _prompt_data_collector
from utils.logger import get_logger

logger = get_logger(__name__)

# ─── Type mapping for dynamic Pydantic model construction ─────────────────────
_TYPE_MAP: Dict[str, type] = {
    "str":   str,
    "int":   int,
    "float": float,
    "bool":  bool,
    "list":  list,
    "dict":  dict,
}

_LOG_LOCK = threading.Lock()   # guards log_callback from concurrent parallel agents


# ─── Dynamic model builders ───────────────────────────────────────────────────

def _build_output_model(output_schema: list, model_name: str = "AgentOutput"):
    """
    Build a Pydantic model at runtime from a list of FieldSchema objects.

    All fields use Any so the LLM can return any native Python value
    (str, int, list, dict, …) without Pydantic rejecting a type mismatch.
    Declared types are enforced *after* the call via _coerce_to_schema().
    This keeps the model fully generic — no tool or field names are hardcoded.
    """
    from typing import Any as AnyT, Optional as Opt
    fields: Dict[str, Any] = {}
    for f in output_schema:
        if f.required:
            fields[f.name] = (AnyT, ...)
        else:
            fields[f.name] = (Opt[AnyT], f.default)
    return create_model(model_name, **fields)


def _build_data_collector_model(output_schema: list):
    """
    Build a Pydantic model for data_collector agents.

    Domain fields use Optional[Any] so the LLM can return any type without
    Pydantic rejecting it (e.g. int 7 for a field declared as str 'days').
    Type coercion to declared types is applied afterwards via _coerce_to_schema().
    Meta-fields for completeness tracking are always present.
    """
    from typing import Any as AnyT, Optional as Opt, List as Lst
    fields: Dict[str, Any] = {}
    for f in output_schema:
        fields[f.name] = (Opt[AnyT], None)
    # Meta fields
    fields["collection_status"]   = (str, ...)            # "complete" | "incomplete"
    fields["follow_up_question"]  = (Opt[str], None)
    fields["missing_fields"]      = (Opt[Lst[str]], None)
    return create_model("DataCollectorOutput", **fields)


def _coerce_to_schema(result_dict: dict, output_schema: list) -> dict:
    """
    Coerce values in result_dict to the declared types in output_schema.

    Applied after every LLM / tool response so type mismatches are silently
    normalised rather than crashing the pipeline.  For example:
      - LLM returns a list  where schema says str  → JSON-serialise it
      - LLM returns an int  where schema says str  → str(val)
      - LLM returns a str   where schema says list → try json.loads()
      - LLM returns a str   where schema says int  → int(val)

    This function is fully generic — it operates purely on the schema
    definition, no tool or agent names are referenced.
    """
    import json
    coerced = dict(result_dict)
    for f in output_schema:
        val = coerced.get(f.name)
        if val is None:
            continue
        target = f.type
        try:
            if target == "str" and not isinstance(val, str):
                coerced[f.name] = (
                    json.dumps(val, ensure_ascii=False)
                    if isinstance(val, (list, dict))
                    else str(val)
                )
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
        except (ValueError, TypeError, Exception):
            pass   # keep original value; pipeline continues with what the LLM returned
    return coerced


# ─── Runners ─────────────────────────────────────────────────────────────────

def _run_deterministic(agent_def, input_values: dict, built: dict, log) -> dict:
    """Execute a deterministic (single-tool, no-LLM) agent."""
    tool_funcs = built["tools"]
    tool_name  = agent_def.tools[0]
    tool_fn    = tool_funcs.get(tool_name)
    if not tool_fn:
        raise ValueError(f"Tool '{tool_name}' not found in registry.")

    log("tool_call", tool=tool_name, input=str(input_values)[:200])

    # Try keyword-argument call first (works for single- and multi-arg tools
    # as long as agent input field names match tool parameter names).
    # Fall back to positional args for all collected inputs (legacy tools).
    try:
        result = tool_fn(**input_values)
    except TypeError:
        positional_args = list(input_values.values()) if input_values else []
        result = tool_fn(*positional_args)
    log("tool_response", tool=tool_name, output=str(result)[:300])

    output_updates = {out_var: result for out_var in agent_def.effective_outputs}
    return output_updates


def _run_data_collector(agent_def, input_values: dict, workflow_state: dict, llm, log) -> dict:
    """
    Execute a data_collector agent.
    - Builds a dynamic Pydantic model from the agent's output_schema.
    - Calls the LLM with with_structured_output to force structured JSON.
    - Checks which required fields are still missing.
    - Returns: domain fields + collection_status + follow_up_question + missing_fields.
    """
    output_schema = agent_def.output_schema
    if not output_schema:
        raise ValueError(
            f"data_collector agent '{agent_def.name}' must have an output_schema defined."
        )

    # Build already-collected context from workflow state
    already_collected = {
        f.name: workflow_state.get(f.name)
        for f in output_schema
        if workflow_state.get(f.name) is not None
    }

    system_prompt = _prompt_data_collector(agent_def, already_collected or None)
    log("dc_prompt_built", already_collected=list(already_collected.keys()))

    # Build and bind the structured output model
    output_model = _build_data_collector_model(output_schema)
    log("dc_output_model_built", fields=[f.name for f in output_schema])

    structured_llm = llm.with_structured_output(output_model)
    log("llm_start", model=agent_def.llm_model, behavior="data_collector")

    # Look for user_message in input_values first (explicit input),
    # then fall back to workflow_state directly (set by resume_workflow),
    # then fall back to joining all input values.
    user_message = (
        input_values.get("user_message")
        or workflow_state.get("user_message", "")
        or " ".join(str(v) for v in input_values.values() if v)
    )
    log("dc_user_message", preview=str(user_message)[:200])
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]

    result = structured_llm.invoke(messages)
    log("llm_complete", collection_status=result.collection_status,
        missing=result.missing_fields or [])

    result_dict = result.model_dump()

    # Coerce domain field values to their declared types (e.g. int→str, list→str)
    result_dict = _coerce_to_schema(result_dict, output_schema)

    # Validate: override collection_status if LLM missed something.
    # Use `is None` (not falsy) so that 0, False, "" are treated as valid values.
    required_names = [f.name for f in output_schema if f.required]
    truly_missing  = [n for n in required_names if result_dict.get(n) is None]

    if truly_missing:
        result_dict["collection_status"]  = "incomplete"
        result_dict["missing_fields"]     = truly_missing
        if not result_dict.get("follow_up_question"):
            result_dict["follow_up_question"] = (
                f"Could you please provide the following information: "
                f"{', '.join(truly_missing)}?"
            )
        log("dc_incomplete", missing=truly_missing,
            follow_up=result_dict["follow_up_question"])
    else:
        result_dict["collection_status"] = "complete"
        result_dict["follow_up_question"] = None
        result_dict["missing_fields"]     = []
        log("dc_complete", extracted=required_names)

    return result_dict


def _run_structured(agent_def, input_values: dict, agent_executor, llm, log) -> dict:
    """
    Execute a task_executor or aggregator agent.
    Phase 1: run through AgentExecutor (tool-calling loop) to get a text result.
    Phase 2: if output_schema is defined, parse result into typed JSON via
             with_structured_output; otherwise fall back to text parsing.
    """
    output_schema = agent_def.output_schema
    input_text = "\n".join(f"{k}: {v}" for k, v in input_values.items()) or "Begin your task."

    log("llm_start", model=agent_def.llm_model,
        behavior=getattr(agent_def, "behavior", "task_executor"),
        input_preview=input_text[:200])

    # ── Phase 1: run AgentExecutor (handles tool calls) ──────────────────────
    result      = agent_executor.invoke({"input": input_text})
    output_text = result.get("output", "")
    log("llm_complete", output_preview=output_text[:300])

    # ── Phase 2: structured parsing when output_schema is defined ────────────
    if output_schema:
        try:
            output_model    = _build_output_model(output_schema, "TaskOutput")
            structured_llm  = llm.with_structured_output(output_model)
            parse_prompt    = (
                f"Extract the following fields from the text below into the required JSON schema.\n\n"
                f"Text:\n{output_text}"
            )
            log("structured_parse_start", fields=[f.name for f in output_schema])
            parsed = structured_llm.invoke(parse_prompt)
            output_updates = _coerce_to_schema(parsed.model_dump(), output_schema)
            log("structured_parse_done", fields=list(output_updates.keys()))
            return output_updates
        except Exception as e:
            log("structured_parse_failed", error=str(e),
                fallback="legacy text parsing")
            # Fall through to legacy parsing

    # ── Legacy: text section parsing ──────────────────────────────────────────
    effective_outputs = agent_def.effective_outputs
    output_updates: Dict[str, Any] = {}

    if len(effective_outputs) == 1:
        # Single output — the entire LLM response belongs to it
        output_updates[effective_outputs[0]] = output_text
    else:
        # Multi-output — scan for "fieldname:" section headers in the text.
        # If a header is not found, store empty string rather than dumping the
        # full response into every unmatched field.
        found_any = False
        for out_var in effective_outputs:
            lines      = output_text.split("\n")
            section    = []
            in_section = False
            for line in lines:
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
        # Last-resort: if nothing was parsed at all, put everything in first field
        if not found_any and effective_outputs:
            output_updates[effective_outputs[0]] = output_text

    return output_updates


# ─── Public entry point ───────────────────────────────────────────────────────

def run_agent(agent_def, workflow_state: dict, log_callback=None) -> dict:
    """
    Execute a single agent within the workflow.

    Returns a dict of new state variables to merge into workflow_state.

    For data_collector agents the return dict will also contain:
      - collection_status  ("complete" | "incomplete")
      - follow_up_question (str | None)
      - missing_fields     (list[str])

    The workflow_runner checks collection_status to decide whether to pause.
    """
    def log(event: str, **kwargs):
        entry = {"event": event, "agent": agent_def.name, "timestamp": time.time(), **kwargs}
        with _LOG_LOCK:
            logger.info(entry)
            if log_callback:
                log_callback(entry)

    behavior = getattr(agent_def, "behavior", "task_executor")
    log("agent_start",
        agent_type=agent_def.agent_type,
        behavior=behavior,
        inputs=agent_def.effective_inputs,
        outputs=agent_def.effective_outputs)

    start = time.time()

    # Extract inputs from workflow state
    input_values = {k: workflow_state.get(k, "") for k in agent_def.effective_inputs}
    log("inputs_extracted",
        inputs={k: str(v)[:120] + ("…" if len(str(v)) > 120 else "") for k, v in input_values.items()})

    try:
        built = build_agent(agent_def)

        # ── Deterministic ────────────────────────────────────────────────────
        if isinstance(built, dict) and built.get("type") == "deterministic":
            log("branch_deterministic")
            output_updates = _run_deterministic(agent_def, input_values, built, log)

        # ── Data collector ───────────────────────────────────────────────────
        elif behavior == "data_collector":
            log("branch_data_collector")
            from llm.llm_provider import get_llm
            llm = get_llm(agent_def.llm_model)
            output_updates = _run_data_collector(agent_def, input_values, workflow_state, llm, log)

        # ── Aggregator (direct chain, no tool loop) ───────────────────────────
        elif behavior == "aggregator":
            log("branch_aggregator")
            from llm.llm_provider import get_llm
            llm = get_llm(agent_def.llm_model)
            output_schema = agent_def.output_schema
            system_prompt = generate_prompt(agent_def)
            input_text    = "\n".join(f"{k}: {v}" for k, v in input_values.items())
            log("llm_start", model=agent_def.llm_model, behavior="aggregator",
                input_preview=input_text[:200])
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=input_text),
            ]

            if output_schema:
                # If ALL output fields are plain str, use a plain LLM call so the
                # response is readable text rather than a JSON/dict structure.
                # Only use with_structured_output when there are multi-typed fields
                # that genuinely need structured JSON (int, list, dict, etc.).
                all_str_fields = all(
                    (f.type or "str") == "str" for f in output_schema
                )

                if all_str_fields:
                    # Plain text response — each field gets the full LLM text
                    result_text = llm.invoke(messages).content
                    log("llm_complete", fields=[f.name for f in output_schema])
                    output_updates = {f.name: result_text for f in output_schema}
                else:
                    # Multi-typed schema — force structured JSON output
                    output_model   = _build_output_model(output_schema, "AggregatorOutput")
                    structured_llm = llm.with_structured_output(output_model)
                    result = structured_llm.invoke(messages)
                    log("llm_complete", fields=list(result.model_dump().keys()))
                    output_updates = _coerce_to_schema(result.model_dump(), output_schema)
            else:
                # No schema — fall back to task_executor path
                output_updates = _run_structured(agent_def, input_values, built, llm, log)

        # ── Task executor (reasoning / hybrid) ───────────────────────────────
        else:
            log("branch_task_executor")
            from llm.llm_provider import get_llm
            llm = get_llm(agent_def.llm_model)
            output_updates = _run_structured(agent_def, input_values, built, llm, log)

        duration_ms = round((time.time() - start) * 1000)
        log("outputs_produced",
            outputs={k: str(v)[:120] + ("…" if len(str(v)) > 120 else "")
                     for k, v in output_updates.items() if k not in
                     ("collection_status", "follow_up_question", "missing_fields")})
        log("agent_complete", duration_ms=duration_ms, behavior=behavior)
        return output_updates

    except Exception as e:
        log("agent_error", error=str(e))
        raise RuntimeError(f"Agent '{agent_def.name}' failed: {str(e)}") from e
