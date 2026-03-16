from typing import Any
from typing_extensions import TypedDict


class WorkflowState(TypedDict, total=False):
    """
    Dynamic workflow state that accumulates all variables produced by agents.
    total=False means all keys are optional — agents add keys as they execute.
    """
    pass


def make_initial_state(user_inputs: dict) -> dict:
    """Create the initial workflow state from user-supplied inputs."""
    return dict(user_inputs)


def merge_state(current_state: dict, updates: dict) -> dict:
    """Merge agent output updates into the current workflow state.

    None values in `updates` do NOT overwrite existing non-None values in
    current_state.  This ensures that a data_collector partial run (which
    returns None for un-extracted fields) cannot erase data that was already
    collected in a previous turn.
    """
    new_state = dict(current_state)
    for k, v in updates.items():
        # Only overwrite if the new value is not None, OR the key is new
        if v is not None or k not in new_state:
            new_state[k] = v
    return new_state
