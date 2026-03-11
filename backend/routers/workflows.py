from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.db import get_db
from database.crud import (
    create_workflow, get_workflow, list_workflows, update_workflow, delete_workflow
)
from backend.schemas.workflow_schema import WorkflowCreate, WorkflowUpdate

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post("")
def create(data: WorkflowCreate, db: Session = Depends(get_db)):
    return create_workflow(db, data)


@router.get("")
def list_all(db: Session = Depends(get_db)):
    return list_workflows(db)


@router.get("/{workflow_id}")
def get_one(workflow_id: str, db: Session = Depends(get_db)):
    wf = get_workflow(db, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.put("/{workflow_id}")
def update(workflow_id: str, data: WorkflowUpdate, db: Session = Depends(get_db)):
    wf = update_workflow(db, workflow_id, data)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.delete("/{workflow_id}")
def delete(workflow_id: str, db: Session = Depends(get_db)):
    success = delete_workflow(db, workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"message": "Workflow deleted successfully"}
