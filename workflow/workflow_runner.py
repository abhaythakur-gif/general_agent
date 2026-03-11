from workflow.workflow_state import make_initial_state, merge_state
from workflow.workflow_validator import validate_workflow
from agents.agent_executor import run_agent
from utils.logger import get_logger

logger = get_logger(__name__)


def run_workflow(
    agent_defs: list,
    initial_inputs: dict,
    log_callback=None,
) -> dict:
    """
    Execute a full sequential workflow.

    Args:
        agent_defs: Ordered list of AgentDefinition objects
        initial_inputs: User-supplied initial variables (e.g. {"topic": "AI in healthcare"})
        log_callback: Optional callable(event_dict) for real-time log streaming

    Returns:
        Final workflow state dict with all variables
    """
    def log(event: str, **kwargs):
        entry = {"event": event, **kwargs}
        logger.info(str(entry))
        if log_callback:
            log_callback(entry)
    
    # Validate before any execution
    errors = validate_workflow(agent_defs)
    if errors:
        raise ValueError("Workflow validation failed:\n" + "\n".join(errors))
    

    state = make_initial_state(initial_inputs)
    log("workflow_start", num_agents=len(agent_defs), initial_inputs=list(initial_inputs.keys()))

    for idx, agent_def in enumerate(agent_defs):
        log("agent_sequence", step=idx + 1, total=len(agent_defs), agent=agent_def.name)
        try:
            updates = run_agent(agent_def, state, log_callback=log_callback)
            state = merge_state(state, updates)
            log("state_updated", new_vars=list(updates.keys()))
        except RuntimeError as e:
            log("workflow_error", step=idx + 1, agent=agent_def.name, error=str(e))
            raise

    log("workflow_complete", final_vars=list(state.keys()))
    return state
