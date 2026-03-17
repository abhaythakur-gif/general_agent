from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.mongo import ensure_indexes
from app.api.v1 import auth, agents, workflows, execution, tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_indexes()
    from app.tools.registry import seed_tools_to_db
    seed_tools_to_db()
    yield


app = FastAPI(
    title="Universal Agent Builder Platform",
    description="A general-purpose no-code agentic workflow builder powered by LangChain & LangGraph.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(workflows.router)
app.include_router(execution.router)
app.include_router(tools.router)


@app.get("/", tags=["System"])
def root():
    return {"message": "Universal Agent Builder Platform API", "docs": "/docs", "version": "1.0.0"}


@app.get("/health", summary="Health check", tags=["System"])
def health():
    return {"status": "ok"}
