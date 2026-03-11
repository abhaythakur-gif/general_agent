from sqlalchemy import Column, String, DateTime, JSON, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from utils.config import settings
import datetime

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AgentModel(Base):
    __tablename__ = "agents"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    agent_type = Column(String, default="reasoning")
    llm_model = Column(String, nullable=True)
    tools = Column(JSON, default=[])
    inputs = Column(JSON, default=[])
    outputs = Column(JSON, default=[])
    created_at = Column(String, default=lambda: datetime.datetime.utcnow().isoformat())


class WorkflowModel(Base):
    __tablename__ = "workflows"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    agent_ids = Column(JSON, default=[])
    created_at = Column(String, default=lambda: datetime.datetime.utcnow().isoformat())


class ExecutionLogModel(Base):
    __tablename__ = "execution_logs"
    id = Column(String, primary_key=True, index=True)
    workflow_id = Column(String, nullable=False)
    started_at = Column(String)
    completed_at = Column(String, nullable=True)
    status = Column(String, default="running")
    log_entries = Column(JSON, default=[])
    final_output = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
