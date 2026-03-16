from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.schemas.workflow import ExecutionRequest
from app.schemas.response import ExecutionResponse, ExecutionDetailResponse, ExecutionLogsResponse, ExecutionListResponse
from app.services.auth_service import get_current_user_id
from app.services import execution_service

router = APIRouter(tags=["Execution"])


@router.post("/workflows/{workflow_id}/execute", summary="Start a workflow execution",
             response_model=ExecutionResponse,
             responses={404: {"description": "Workflow or agent not found"}, 500: {"description": "Runner error"}})
def execute_workflow(workflow_id: str, request: ExecutionRequest, user_id: str = Depends(get_current_user_id)):
    """
    Trigger a full workflow run.

    **Request:** `{ "initial_inputs": { "text": "I love this product" } }`

    Returns `status: "completed"` or `status: "paused"` (needs resume).
    """
    return execution_service.execute_workflow(
        workflow_id=workflow_id, initial_inputs=request.initial_inputs, user_id=user_id,
    )


class ResumeRequest(BaseModel):
    user_input: str


@router.post("/executions/{execution_id}/resume", summary="Resume a paused workflow execution",
             response_model=ExecutionResponse,
             responses={404: {"description": "Execution not found or not paused"}})
def resume_execution(execution_id: str, request: ResumeRequest):
    """
    Resume a paused execution with the user's answer to `follow_up_question`.

    **Request:** `{ "user_input": "My departure date is March 20th" }`
    """
    return execution_service.resume_execution(execution_id=execution_id, user_input=request.user_input)


@router.get("/executions/{execution_id}", summary="Get execution status and result",
            response_model=ExecutionDetailResponse,
            responses={404: {"description": "Execution not found"}})
def get_execution(execution_id: str):
    return execution_service.get_execution(execution_id)


@router.get("/executions/{execution_id}/logs", summary="Get step-by-step agent logs",
            response_model=ExecutionLogsResponse,
            responses={404: {"description": "Execution not found"}})
def get_logs(execution_id: str):
    return execution_service.get_execution_logs(execution_id)


@router.get("/executions", summary="List all past executions for the current user",
            response_model=ExecutionListResponse)
def list_executions(user_id: str = Depends(get_current_user_id)):
    executions = execution_service.list_executions(user_id)
    return {"executions": executions, "total": len(executions)}
