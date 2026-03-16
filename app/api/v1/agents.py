from fastapi import APIRouter, Depends
from app.schemas.agent import AgentCreate, AgentUpdate
from app.schemas.response import AgentResponse, AgentListResponse, AgentDeleteResponse
from app.services.auth_service import get_current_user_id
from app.services import agent_service

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("", summary="Create a new agent", response_model=AgentResponse, status_code=201,
             responses={201: {"description": "Agent created"}, 400: {"description": "Validation error"}})
def create(data: AgentCreate, user_id: str = Depends(get_current_user_id)):
    """
    Create a new agent. **Required header:** `X-User-ID: <your-user-id>`

    ```json
    {
      "name": "Sentiment Analyzer", "description": "Classifies text sentiment",
      "agent_type": "reasoning", "behavior": "task_executor", "llm_model": "gpt-4",
      "tools": [], "input_schema": [{"name": "text", "type": "str", "required": true}],
      "output_schema": [{"name": "sentiment", "type": "str", "allowed_values": ["positive","negative","neutral"]}]
    }
    ```
    """
    return agent_service.create_agent(data, user_id)


@router.get("", summary="List all agents for the current user", response_model=AgentListResponse)
def list_all(user_id: str = Depends(get_current_user_id)):
    agents = agent_service.list_agents(user_id)
    return {"agents": agents, "total": len(agents)}


@router.get("/{agent_id}", summary="Get a single agent by ID", response_model=AgentResponse,
            responses={404: {"description": "Agent not found"}})
def get_one(agent_id: str, user_id: str = Depends(get_current_user_id)):
    return agent_service.get_agent(agent_id, user_id)


@router.put("/{agent_id}", summary="Update an agent", response_model=AgentResponse,
            responses={404: {"description": "Agent not found"}})
def update(agent_id: str, data: AgentUpdate, user_id: str = Depends(get_current_user_id)):
    return agent_service.update_agent(agent_id, user_id, data)


@router.delete("/{agent_id}", summary="Delete an agent", response_model=AgentDeleteResponse,
               responses={404: {"description": "Agent not found"}})
def delete(agent_id: str, user_id: str = Depends(get_current_user_id)):
    return agent_service.delete_agent(agent_id, user_id)
