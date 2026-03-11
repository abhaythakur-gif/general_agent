from sqlalchemy.orm import Session
from database.db import AgentModel, WorkflowModel, ExecutionLogModel
from backend.schemas.agent_schema import AgentCreate, AgentUpdate, AgentDefinition
from backend.schemas.workflow_schema import WorkflowCreate, WorkflowUpdate, WorkflowDefinition, ExecutionLog
import uuid
from datetime import datetime


# ─── AGENT CRUD ─────────────────────────────────────────────────────────────

def create_agent(db: Session, data: AgentCreate) -> AgentModel:
    agent = AgentModel(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        agent_type=data.agent_type,
        llm_model=data.llm_model,
        tools=data.tools,
        inputs=data.inputs,
        outputs=data.outputs,
        created_at=datetime.utcnow().isoformat(),
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def get_agent(db: Session, agent_id: str) -> AgentModel | None:
    return db.query(AgentModel).filter(AgentModel.id == agent_id).first()


def list_agents(db: Session) -> list[AgentModel]:
    return db.query(AgentModel).all()


def update_agent(db: Session, agent_id: str, data: AgentUpdate) -> AgentModel | None:
    agent = get_agent(db, agent_id)
    if not agent:
        return None
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(agent, field, value)
    db.commit()
    db.refresh(agent)
    return agent


def delete_agent(db: Session, agent_id: str) -> bool:
    agent = get_agent(db, agent_id)
    if not agent:
        return False
    db.delete(agent)
    db.commit()
    return True


# ─── WORKFLOW CRUD ───────────────────────────────────────────────────────────

def create_workflow(db: Session, data: WorkflowCreate) -> WorkflowModel:
    wf = WorkflowModel(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        agent_ids=data.agent_ids,
        created_at=datetime.utcnow().isoformat(),
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


def get_workflow(db: Session, workflow_id: str) -> WorkflowModel | None:
    return db.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()


def list_workflows(db: Session) -> list[WorkflowModel]:
    return db.query(WorkflowModel).all()


def update_workflow(db: Session, workflow_id: str, data: WorkflowUpdate) -> WorkflowModel | None:
    wf = get_workflow(db, workflow_id)
    if not wf:
        return None
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(wf, field, value)
    db.commit()
    db.refresh(wf)
    return wf


def delete_workflow(db: Session, workflow_id: str) -> bool:
    wf = get_workflow(db, workflow_id)
    if not wf:
        return False
    db.delete(wf)
    db.commit()
    return True


# ─── EXECUTION LOG CRUD ──────────────────────────────────────────────────────

def create_execution_log(db: Session, workflow_id: str) -> ExecutionLogModel:
    log = ExecutionLogModel(
        id=str(uuid.uuid4()),
        workflow_id=workflow_id,
        started_at=datetime.utcnow().isoformat(),
        status="running",
        log_entries=[],
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_execution_log(db: Session, log_id: str) -> ExecutionLogModel | None:
    return db.query(ExecutionLogModel).filter(ExecutionLogModel.id == log_id).first()


def append_log_entry(db: Session, log_id: str, entry: dict):
    log = get_execution_log(db, log_id)
    if log:
        entries = list(log.log_entries or [])
        entries.append(entry)
        log.log_entries = entries
        db.commit()


def complete_execution(db: Session, log_id: str, final_output: dict):
    log = get_execution_log(db, log_id)
    if log:
        log.status = "completed"
        log.completed_at = datetime.utcnow().isoformat()
        log.final_output = final_output
        db.commit()


def fail_execution(db: Session, log_id: str, error_message: str):
    log = get_execution_log(db, log_id)
    if log:
        log.status = "failed"
        log.completed_at = datetime.utcnow().isoformat()
        log.error_message = error_message
        db.commit()
