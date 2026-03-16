import re
from app.tools.registry import tool_registry

_IGNORED_TOKENS = {"and", "or", "not", "in", "is", "true", "false", "none"}
_DC_IMPLICIT_OUTPUTS = {"collection_status", "follow_up_question", "missing_fields"}


def _extract_var_names(expression: str) -> set:
    cleaned = re.sub(r'"[^"]*"', '', expression)
    cleaned = re.sub(r"'[^']*'", '', cleaned)
    tokens  = re.findall(r"\b[a-z_][a-z0-9_]*\b", cleaned, re.IGNORECASE)
    return {t.lower() for t in tokens} - _IGNORED_TOKENS


def _output_type_map(agent) -> dict:
    if agent.output_schema:
        return {f.name: f.type for f in agent.output_schema}
    return {name: "str" for name in agent.outputs}


def validate_workflow(agent_defs: list) -> list:
    errors:   list = []
    warnings: list = []
    available_vars: dict = {}

    for idx, agent in enumerate(agent_defs):
        position = idx + 1
        behavior = getattr(agent, "behavior", "task_executor")

        for tool_name in agent.tools:
            if tool_name not in tool_registry:
                errors.append(f"Agent {position} ('{agent.name}'): tool '{tool_name}' is not registered.")

        check_inputs = agent.input_schema if agent.input_schema else [
            type('_F', (), {'name': n, 'type': 'str', 'required': True})()
            for n in agent.inputs
        ]
        for field in check_inputs:
            inp = field.name
            if inp not in available_vars:
                if idx > 0:
                    errors.append(
                        f"Agent {position} ('{agent.name}'): requires input '{inp}' "
                        f"but no previous agent produces it. Available: {sorted(available_vars.keys())}"
                    )
            else:
                expected_type = getattr(field, 'type', 'str')
                actual_type   = available_vars[inp]
                if expected_type != actual_type and actual_type != "str":
                    warnings.append(
                        f"Agent {position} ('{agent.name}'): input '{inp}' expects "
                        f"type '{expected_type}' but upstream produces '{actual_type}'."
                    )

        run_if_raw = getattr(agent, "run_if", None)
        run_if = run_if_raw.strip() if isinstance(run_if_raw, str) else run_if_raw
        run_if = run_if or None

        if idx > 0 and not run_if:
            any_prior_has_condition = any(
                (getattr(a, "run_if", None) or "").strip() for a in agent_defs[:idx]
            )
            if any_prior_has_condition:
                warnings.append(
                    f"Agent {position} ('{agent.name}'): no condition set but earlier agents have conditions. "
                    f"This agent will ALWAYS run."
                )

        if run_if:
            try:
                eval(run_if, {"__builtins__": {}}, {})
            except SyntaxError as exc:
                errors.append(f"Agent {position} ('{agent.name}'): condition syntax error — '{run_if}' ({exc})")
            except Exception:
                pass

            for var in _extract_var_names(run_if):
                if var not in available_vars:
                    errors.append(
                        f"Agent {position} ('{agent.name}'): condition references '{var}' "
                        f"but no previous agent produces it. Available: {sorted(available_vars.keys())}"
                    )

        for var_name, type_str in _output_type_map(agent).items():
            available_vars[var_name] = type_str

        if behavior == "data_collector":
            available_vars["collection_status"]  = "str"
            available_vars["follow_up_question"] = "str"
            available_vars["missing_fields"]     = "list"

    return errors + [f"[WARNING] {w}" for w in warnings]
