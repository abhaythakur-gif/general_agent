"""
app/controllers — HTTP layer (MVC Controller tier)
===================================================
All FastAPI route handlers live here, organised by resource group.
Each sub-package owns its own request/response schemas so every
concern is co-located and self-documenting.

Folder structure
----------------
controllers/
├── agent/
│   ├── agent_controller.py          ← FastAPI routes for /api/v1/agents
│   └── schema/
│       ├── request/
│       │   └── agent_request.py     ← CreateAgentRequest, UpdateAgentRequest
│       └── response/
│           └── agent_response.py    ← AgentOut, AgentListOut, AgentDeleteOut
│
├── workflow/
│   ├── workflow_controller.py       ← /api/v1/workflows
│   └── schema/
│       ├── request/
│       │   └── workflow_request.py  ← CreateWorkflowRequest, UpdateWorkflowRequest
│       └── response/
│           └── workflow_response.py ← WorkflowOut, WorkflowListOut, WorkflowDeleteOut
│
├── execution/
│   ├── execution_controller.py      ← /api/v1/workflows/{id}/execute, /api/v1/executions
│   └── schema/
│       ├── request/
│       │   └── execution_request.py ← ExecuteWorkflowRequest, ResumeExecutionRequest
│       └── response/
│           └── execution_response.py← ExecutionOut, ExecutionDetailOut, ExecutionLogsOut, ExecutionListOut
│
├── auth/
│   ├── auth_controller.py           ← /api/v1/auth
│   └── schema/
│       ├── request/
│       │   └── auth_request.py      ← AuthInitRequest
│       └── response/
│           └── auth_response.py     ← AuthInitOut, UserProfileOut
│
├── tools/
│   ├── tools_controller.py          ← /api/v1/tools, /api/v1/models
│   └── schema/
│       └── response/
│           └── tools_response.py    ← ToolsListOut, ModelsListOut
│
├── chat/
│   ├── chat_controller.py           ← /api/v1/chat/sessions
│   └── schema/
│       ├── request/
│       │   └── chat_request.py      ← CreateChatSessionRequest, SendMessageRequest
│       └── response/
│           └── chat_response.py     ← ChatSessionOut, ChatReplyOut, ChatHistoryOut …
│
└── router/
    ├── router_controller.py         ← /api/v1/routers
    └── schema/
        ├── request/
        │   └── router_request.py    ← CreateRouterRequest, UpdateRouterRequest, RouterDispatchRequest
        └── response/
            └── router_response.py   ← RouterOut, RouterListOut, RouterDeleteOut, RouterDispatchOut
"""
