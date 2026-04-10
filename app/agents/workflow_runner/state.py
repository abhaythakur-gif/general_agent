from typing import Any
from typing_extensions import TypedDict


class WorkflowState(TypedDict, total=False):
    pass


def make_initial_state(user_inputs: dict) -> dict:
    return dict(user_inputs)


def merge_state(current_state: dict, updates: dict) -> dict:
    new_state = dict(current_state)
    for k, v in updates.items():
        if v is not None or k not in new_state:
            new_state[k] = v
    return new_state
