"""
app/agentic/agents/workflow_runner/agent.py
--------------------------------------------
Executes sequential, conditional, and parallel workflows with full
pause/resume support for data_collector agents (human-in-the-loop).
Replaces app/engine/workflow/runner.py.

Public API
----------
start_workflow(agent_defs, initial_inputs, workflow_id, parallel_groups, log_callback)
    → WorkflowResult dict

resume_workflow(execution_id, user_input, log_callback)
    → WorkflowResult dict

WorkflowResult keys:
  status              "completed" | "paused" | "failed"
  state               full workflow state dict
  execution_id        str
  follow_up_question  str | None   (set when status == "paused")
  paused_at_agent     str | None
  missing_fields      list[str]
  logs                list[dict]
"""

import uuid
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Callable, List, Optional

from app.agentic.agents.workflow_runner.state import make_initial_state, merge_state
from app.agentic.agents.workflow_runner.validator import validate_workflow
from app.agentic.agents.reasoning.agent import run_agent
from app.config.logging import get_logger
from app.utils.common import storage

logger = get_logger(__name__)


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _evaluate_condition(expression: str, state: dict, agent_name: str) -> bool:
    normalised = {
        k: (v.strip().lower() if isinstance(v, str) else v)
        for k, v in state.items()
    }
    try:
        result = eval(expression, {"__builtins__": {}}, normalised)
        return bool(result)
    except NameError as exc:
        raise RuntimeError(
            f"Condition for agent '{agent_name}' references an unknown variable: "
            f"'{expression}' — {exc}. "
            f"Available state variables: {sorted(state.keys())}"
        ) from exc
    except SyntaxError as exc:
        raise RuntimeError(
            f"Condition for agent '{agent_name}' has a syntax error: "
            f"'{expression}' — {exc}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"Condition for agent '{agent_name}' could not be evaluated: "
            f"'{expression}' — {exc}"
        ) from exc


def _build_parallel_map(parallel_groups: List[List[str]]) -> dict:
    m = {}
    for group in parallel_groups:
        fs = frozenset(group)
        for aid in group:
            m[aid] = fs
    return m


def _agent_defs_by_id(agent_defs: list) -> dict:
    return {a.id: a for a in agent_defs}


def _serialize_agent_defs(agent_defs: list) -> list:
    return [a.dict() for a in agent_defs]


def _deserialize_agent_defs(raw: list):
    from app.models.domain.agent import AgentDefinition
    return [AgentDefinition(**d) for d in raw]


# ─── Core execution loop ──────────────────────────────────────────────────────

def _execute_from(
    agent_defs:     list,
    state:          dict,
    start_idx:      int,
    parallel_groups: List[List[str]],
    log_callback:   Optional[Callable],
    execution_id:   str,
    collected_logs: list,
) -> dict:
    def log(event: str, **kwargs):
        entry = {"event": event, "timestamp": time.time(), **kwargs}
        logger.info(str(entry))
        collected_logs.append(entry)
        if log_callback:
            log_callback(entry)

    parallel_map  = _build_parallel_map(parallel_groups)
    by_id         = _agent_defs_by_id(agent_defs)
    parallel_done = set()
    skipped_agents: List[str] = []

    total = len(agent_defs)

    for idx in range(start_idx, total):
        agent_def = agent_defs[idx]
        log("agent_sequence", step=idx + 1, total=total, agent=agent_def.name)

        # ── Parallel group check ──────────────────────────────────────────────
        group_key = parallel_map.get(agent_def.id)
        if group_key is not None:
            if group_key in parallel_done:
                log("parallel_agent_already_ran", step=idx + 1, agent=agent_def.name,
                    reason="executed as part of a parallel group earlier")
                continue

            group_agents = [by_id[aid] for aid in group_key if aid in by_id]
            log("parallel_group_start", step=idx + 1, agents=[a.name for a in group_agents])

            group_updates: dict = {}
            errors: List[str] = []

            with ThreadPoolExecutor(max_workers=len(group_agents)) as executor:
                futures = {
                    executor.submit(run_agent, a, state, log_callback): a
                    for a in group_agents
                }
                for future in as_completed(futures):
                    ag = futures[future]
                    try:
                        updates = future.result()
                        group_updates.update(updates)
                        log("parallel_agent_done", agent=ag.name, produced=list(updates.keys()))
                    except Exception as e:
                        errors.append(f"Agent '{ag.name}': {e}")
                        log("parallel_agent_error", agent=ag.name, error=str(e))

            if errors:
                raise RuntimeError("Parallel group failed:\n" + "\n".join(errors))

            state = merge_state(state, group_updates)
            parallel_done.add(group_key)
            log("parallel_group_done", agents=[a.name for a in group_agents],
                new_vars=list(group_updates.keys()))
            continue

        # ── Condition gate ────────────────────────────────────────────────────
        run_if_raw = getattr(agent_def, "run_if", None)
        run_if = run_if_raw.strip() if isinstance(run_if_raw, str) else run_if_raw
        run_if = run_if or None

        if run_if:
            log("condition_check", step=idx + 1, agent=agent_def.name, condition=run_if)
            try:
                should_run = _evaluate_condition(run_if, state, agent_def.name)
            except RuntimeError as exc:
                log("workflow_error", step=idx + 1, agent=agent_def.name, error=str(exc))
                raise
            log("condition_result", step=idx + 1, agent=agent_def.name,
                condition=run_if, result=should_run)
            if not should_run:
                log("agent_skipped", step=idx + 1, agent=agent_def.name,
                    condition=run_if, reason="condition evaluated to False")
                skipped_agents.append(agent_def.name)
                continue
        else:
            log("condition_check", step=idx + 1, agent=agent_def.name, condition=None)

        # ── Run agent ─────────────────────────────────────────────────────────
        try:
            updates = run_agent(agent_def, state, log_callback=log_callback)
        except RuntimeError as e:
            log("workflow_error", step=idx + 1, agent=agent_def.name, error=str(e))
            raise

        state = merge_state(state, updates)
        log("state_updated", new_vars=list(updates.keys()))

        # ── Pause check for data_collector ────────────────────────────────────
        behavior = getattr(agent_def, "behavior", "task_executor")
        if behavior == "data_collector":
            collection_status = updates.get("collection_status", "complete")
            log("data_collector_status", agent=agent_def.name,
                collection_status=collection_status,
                missing=updates.get("missing_fields", []))

            if collection_status == "incomplete":
                storage.update_execution(execution_id, {
                    "status":             "paused",
                    "current_step":       idx,
                    "paused_agent_name":  agent_def.name,
                    "follow_up_question": updates.get("follow_up_question"),
                    "missing_fields":     updates.get("missing_fields", []),
                    "state":              state,
                    "log_entries":        collected_logs,
                })
                log("workflow_paused", step=idx + 1, agent=agent_def.name,
                    follow_up=updates.get("follow_up_question"))
                return {
                    "status":             "paused",
                    "state":              state,
                    "execution_id":       execution_id,
                    "follow_up_question": updates.get("follow_up_question"),
                    "paused_at_agent":    agent_def.name,
                    "missing_fields":     updates.get("missing_fields", []),
                    "logs":               collected_logs,
                }

    # ── Workflow complete ─────────────────────────────────────────────────────
    log("workflow_complete", final_vars=list(state.keys()), skipped_agents=skipped_agents)
    storage.update_execution(execution_id, {
        "status":      "completed",
        "state":       state,
        "log_entries": collected_logs,
    })
    return {
        "status":             "completed",
        "state":              state,
        "execution_id":       execution_id,
        "follow_up_question": None,
        "paused_at_agent":    None,
        "missing_fields":     [],
        "logs":               collected_logs,
    }


# ─── Public API ───────────────────────────────────────────────────────────────

def start_workflow(
    agent_defs:      list,
    initial_inputs:  dict,
    workflow_id:     str = "",
    parallel_groups: List[List[str]] = None,
    log_callback:    Optional[Callable] = None,
    user_id:         str = "__anonymous__",
) -> dict:
    if parallel_groups is None:
        parallel_groups = []

    collected_logs: List[dict] = []

    def log(event: str, **kwargs):
        entry = {"event": event, "timestamp": time.time(), **kwargs}
        logger.info(str(entry))
        collected_logs.append(entry)
        if log_callback:
            log_callback(entry)

    all_messages = validate_workflow(agent_defs)
    hard_errors  = [m for m in all_messages if not m.startswith("[WARNING]")]
    if hard_errors:
        raise ValueError("Workflow validation failed:\n" + "\n".join(hard_errors))
    for w in [m for m in all_messages if m.startswith("[WARNING]")]:
        log("validation_warning", message=w)

    execution_id = str(uuid.uuid4())
    exec_record  = {
        "id":                 execution_id,
        "user_id":            user_id,
        "workflow_id":        workflow_id,
        "status":             "running",
        "current_step":       0,
        "paused_agent_name":  None,
        "follow_up_question": None,
        "missing_fields":     [],
        "state":              {},
        "agent_defs_raw":     _serialize_agent_defs(agent_defs),
        "parallel_groups":    parallel_groups,
        "log_entries":        [],
        "started_at":         datetime.utcnow().isoformat(),
        "updated_at":         datetime.utcnow().isoformat(),
    }
    storage.save_execution(exec_record)

    state = make_initial_state(initial_inputs)
    log("workflow_start", execution_id=execution_id, num_agents=len(agent_defs),
        initial_inputs=list(initial_inputs.keys()), parallel_groups=parallel_groups)

    return _execute_from(
        agent_defs, state, 0, parallel_groups, log_callback, execution_id, collected_logs,
    )


def resume_workflow(
    execution_id: str,
    user_input:   str,
    log_callback: Optional[Callable] = None,
) -> dict:
    collected_logs: List[dict] = []

    def log(event: str, **kwargs):
        entry = {"event": event, "timestamp": time.time(), **kwargs}
        logger.info(str(entry))
        collected_logs.append(entry)
        if log_callback:
            log_callback(entry)

    exec_record = storage.get_execution(execution_id)
    if not exec_record:
        raise ValueError(f"Execution '{execution_id}' not found.")
    if exec_record.get("status") != "paused":
        raise ValueError(
            f"Execution '{execution_id}' is not paused (status={exec_record.get('status')})."
        )

    state           = exec_record.get("state", {})
    current_step    = exec_record.get("current_step", 0)
    parallel_groups = exec_record.get("parallel_groups", [])
    agent_defs      = _deserialize_agent_defs(exec_record.get("agent_defs_raw", []))
    prev_logs       = exec_record.get("log_entries", [])

    collected_logs.extend(prev_logs)
    state["user_message"] = user_input

    log("workflow_resume", execution_id=execution_id, resume_step=current_step,
        paused_agent=exec_record.get("paused_agent_name"),
        new_input_preview=user_input[:120])

    storage.update_execution(execution_id, {"status": "running"})

    return _execute_from(
        agent_defs, state, current_step, parallel_groups,
        log_callback, execution_id, collected_logs,
    )


def run_workflow(
    agent_defs:      list,
    initial_inputs:  dict,
    log_callback:    Optional[Callable] = None,
) -> dict:
    """Legacy entry point kept for backward compatibility."""
    return start_workflow(
        agent_defs=agent_defs,
        initial_inputs=initial_inputs,
        workflow_id="",
        parallel_groups=[],
        log_callback=log_callback,
    )
