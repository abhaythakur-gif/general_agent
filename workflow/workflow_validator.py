import re
from tools.tool_registry import tool_registry

# Python keywords / operators that appear as identifiers in condition expressions
_IGNORED_TOKENS = {"and", "or", "not", "in", "is", "true", "false", "none"}

# Fields written to state by the runner when a data_collector pauses/completes
_DC_IMPLICIT_OUTPUTS = {"collection_status", "follow_up_question", "missing_fields"}


def _extract_var_names(expression: str) -> set:
    """Return all identifier tokens in a condition expression that are NOT Python keywords
    and NOT string literal contents."""
    cleaned = re.sub(r'"[^"]*"', '', expression)
    cleaned = re.sub(r"'[^']*'", '', cleaned)
    tokens  = re.findall(r"\b[a-z_][a-z0-9_]*\b", cleaned, re.IGNORECASE)
    return {t.lower() for t in tokens} - _IGNORED_TOKENS


def _output_type_map(agent) -> dict:
    """
    Return {field_name: type_str} for an agent's output schema.
    Falls back to "str" for every output if no rich schema is defined.
    """
    if agent.output_schema:
        return {f.name: f.type for f in agent.output_schema}
    return {name: "str" for name in agent.outputs}


def validate_workflow(agent_defs: list) -> list:
    """
    Validate a sequence of agent definitions before execution.

    Checks:
    1. All referenced tools exist in the registry.
    2. All required agent inputs are produced by a prior agent (or come
       from the user on step 1).
    3. Type compatibility: if agent A outputs field X as type T1 and
       agent B expects X as type T2, warn if T1 != T2.
    4. Condition expression syntax and variable references.
    5. data_collector implicit outputs (collection_status, etc.) are
       automatically added to available_vars so downstream conditions work.

    Returns a list of message strings. Hard errors are plain strings.
    Warnings are prefixed with "[WARNING] ".
    """
    errors:   list = []
    warnings: list = []

    # available_vars: {var_name: type_str}
    available_vars: dict = {}

    for idx, agent in enumerate(agent_defs):
        position = idx + 1
        behavior = getattr(agent, "behavior", "task_executor")

        # ── 1. Tool registry check ────────────────────────────────────────────
        for tool_name in agent.tools:
            if tool_name not in tool_registry:
                errors.append(
                    f"Agent {position} ('{agent.name}'): tool '{tool_name}' is not registered."
                )
        
        # ── 2. Input availability + type compat ───────────────────────────────
        check_inputs = agent.input_schema if agent.input_schema else [
            type('_F', (), {'name': n, 'type': 'str', 'required': True})()
            for n in agent.inputs
        ]
        for field in check_inputs:
            inp = field.name
            if inp not in available_vars:
                if idx == 0:
                    pass  # first agent's inputs come from user — allowed
                else:
                    errors.append(
                        f"Agent {position} ('{agent.name}'): requires input '{inp}' "
                        f"but no previous agent produces it. "
                        f"Available variables: {sorted(available_vars.keys())}"
                    )
            else:
                # Type compatibility check
                expected_type = getattr(field, 'type', 'str')
                actual_type   = available_vars[inp]
                if expected_type != actual_type and actual_type != "str":
                    # "str" is a common fallback — downgrade to warning
                    warnings.append(
                        f"Agent {position} ('{agent.name}'): input '{inp}' expects "
                        f"type '{expected_type}' but upstream produces type "
                        f"'{actual_type}'. This may cause runtime errors."
                    )

        # ── 3. Condition expression validation ────────────────────────────────
        run_if = getattr(agent, "run_if", None)
        if run_if:
            try:
                eval(run_if, {"__builtins__": {}}, {})
            except SyntaxError as exc:
                errors.append(
                    f"Agent {position} ('{agent.name}'): condition has a syntax error — "
                    f"'{run_if}' ({exc})"
                )
            except Exception:
                pass  # NameError etc. acceptable at build time

            referenced_vars = _extract_var_names(run_if)
            for var in referenced_vars:
                if var not in available_vars:
                    is_conditional_output = False
                    for prev_idx in range(idx):
                        prev = agent_defs[prev_idx]
                        prev_outputs = [f.name for f in prev.output_schema] if prev.output_schema else prev.outputs
                        if var in prev_outputs and getattr(prev, "run_if", None):
                            is_conditional_output = True
                            break
                    if is_conditional_output:
                        warnings.append(
                            f"Agent {position} ('{agent.name}'): condition references '{var}' "
                            f"which is produced by a conditional agent — it may not exist at "
                            f"runtime if that agent was skipped."
                        )
                    else:
                        errors.append(
                            f"Agent {position} ('{agent.name}'): condition references '{var}' "
                            f"but no previous agent produces it. "
                            f"Available variables: {sorted(available_vars.keys())}"
                        )

        # ── 4. Add this agent's outputs to available_vars ─────────────────────
        for var_name, type_str in _output_type_map(agent).items():
            available_vars[var_name] = type_str

        # data_collector always makes these available to downstream conditions
        if behavior == "data_collector":
            available_vars["collection_status"]   = "str"
            available_vars["follow_up_question"]  = "str"
            available_vars["missing_fields"]      = "list"

    return errors + [f"[WARNING] {w}" for w in warnings]
