from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.mongo import ensure_indexes
from app.controllers.auth.auth_controller import router as auth_router
from app.controllers.agent.agent_controller import router as agents_router
from app.controllers.workflow.workflow_controller import router as workflows_router
from app.controllers.execution.execution_controller import router as execution_router
from app.controllers.tools.tools_controller import router as tools_router
from app.controllers.chat.chat_controller import router as chat_router
from app.controllers.router.router_controller import router as routers_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_indexes()
    from app.tools.registry import seed_tools_to_db
    seed_tools_to_db()
    yield


app = FastAPI(
    title="Universal Agent Builder Platform",
    description=(
        "A general-purpose no-code agentic workflow builder powered by LangChain & LangGraph.\n\n"
        "## Architecture\n"
        "All HTTP endpoints follow **MVC architecture**:\n"
        "- **Controllers** (`app/controllers/`) — HTTP routing, request validation, response serialisation\n"
        "- **Services** (`app/services/`) — business logic\n"
        "- **Repositories** (`app/repositories/`) — MongoDB persistence\n\n"
        "## API Groups\n"
        "| Group | Prefix | Description |\n"
        "|-------|--------|-------------|\n"
        "| Auth | `/auth` | User initialisation and profile |\n"
        "| Agents | `/agents` | Create and manage agent definitions |\n"
        "| Workflows | `/workflows` | Link agents into named workflows |\n"
        "| Execution | `/workflows/{id}/execute`, `/executions` | Trigger and inspect runs |\n"
        "| Tools & Models | `/tools`, `/models` | Browse available tools and LLMs |\n"
        "| Chat | `/chat/sessions` | Persistent multi-turn LLM conversations |\n"
        "| Custom Routers | `/routers` | LLM-powered query dispatch to workflows |\n"
    ),
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

API_PREFIX = "/api/v1"

app.include_router(auth_router,      prefix=API_PREFIX)
app.include_router(agents_router,    prefix=API_PREFIX)
app.include_router(workflows_router, prefix=API_PREFIX)
app.include_router(execution_router, prefix=API_PREFIX)
app.include_router(tools_router,     prefix=API_PREFIX)
app.include_router(chat_router,      prefix=API_PREFIX)
app.include_router(routers_router,   prefix=API_PREFIX)


@app.get("/", tags=["System"])
def root():
    return {"message": "Universal Agent Builder Platform API", "docs": "/docs", "version": "1.0.0"}


@app.get("/health", summary="Health check", tags=["System"])
def health():
    return {"status": "ok"}
