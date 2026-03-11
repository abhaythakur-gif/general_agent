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
    """Merge agent output updates into the current workflow state."""
    new_state = dict(current_state)
    new_state.update(updates)
    return new_state
