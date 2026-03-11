from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.db import create_tables
from backend.routers import agents, workflows, execution, tools

app = FastAPI(
    title="Universal Agent Builder Platform",
    description="A general-purpose no-code agentic workflow builder powered by LangChain & LangGraph.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    create_tables()


app.include_router(agents.router)
app.include_router(workflows.router)
app.include_router(execution.router)
app.include_router(tools.router)


@app.get("/")
def root():
    return {
        "message": "Universal Agent Builder Platform API",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
