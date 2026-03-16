from fastapi import APIRouter, Depends
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate
from app.schemas.response import WorkflowResponse, WorkflowListResponse, WorkflowDeleteResponse
from app.services.auth_service import get_current_user_id
from app.services import workflow_service

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post("", summary="Create a new workflow", response_model=WorkflowResponse, status_code=201,
             responses={400: {"description": "One or more agent_ids do not exist"}})
def create(data: WorkflowCreate, user_id: str = Depends(get_current_user_id)):
    """
    Create a workflow linking existing agents.

    ```json
    {
      "name": "Sentiment Pipeline", "description": "Search → Analyse → Report",
      "agent_ids": ["<agent-uuid-1>", "<agent-uuid-2>"],
      "workflow_type": "conditional",
      "conditions": {"<agent-uuid-2>": "sentiment == 'negative'"},
      "parallel_groups": []
    }
    ```
    """
    return workflow_service.create_workflow(data, user_id)


@router.get("", summary="List all workflows for the current user", response_model=WorkflowListResponse)
def list_all(user_id: str = Depends(get_current_user_id)):
    workflows = workflow_service.list_workflows(user_id)
    return {"workflows": workflows, "total": len(workflows)}


@router.get("/{workflow_id}", summary="Get a single workflow by ID", response_model=WorkflowResponse,
            responses={404: {"description": "Workflow not found"}})
def get_one(workflow_id: str, user_id: str = Depends(get_current_user_id)):
    return workflow_service.get_workflow(workflow_id, user_id)


@router.put("/{workflow_id}", summary="Update a workflow", response_model=WorkflowResponse,
            responses={404: {"description": "Workflow not found"}})
def update(workflow_id: str, data: WorkflowUpdate, user_id: str = Depends(get_current_user_id)):
    return workflow_service.update_workflow(workflow_id, user_id, data)


@router.delete("/{workflow_id}", summary="Delete a workflow", response_model=WorkflowDeleteResponse,
               responses={404: {"description": "Workflow not found"}})
def delete(workflow_id: str, user_id: str = Depends(get_current_user_id)):
    return workflow_service.delete_workflow(workflow_id, user_id)
