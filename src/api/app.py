from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.admin_users import router as admin_users_router
from .routes.admin_workspaces import router as admin_workspaces_router
from .routes.agents import router as agents_router
from .routes.appointments import router as appointments_router
from .routes.auth import router as auth_router
from .routes.chat import router as chat_router
from .routes.conversations import router as conversations_router
from .routes.demo_request import router as demo_request_router
from .routes.escalation import router as escalation_router
from .routes.feedback import router as feedback_router
from .routes.invitations import router as invitations_router
from .routes.knowledge_management import router as knowledge_management_router
from .routes.notifications import router as notifications_router
from .routes.org_signup import router as org_signup_router
from .routes.workspace_admins import router as workspace_admins_router
from .routes.profile import router as profile_router
from .routes.saved_items import router as saved_items_router
from .routes.solutions import router as solutions_router
from .routes.workspace import router as workspace_router

load_dotenv()

app = FastAPI(title="Ha-Shem RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    # Phase 23: opened to any origin so the embeddable SDK can be loaded
    # from arbitrary third-party sites. Safe for the existing frontend,
    # which authenticates via a Bearer header (localStorage-backed), never
    # cookies — credentials mode has no effect on custom-header auth, and
    # allow_origins="*" is only valid (per browser CORS rules) paired with
    # allow_credentials=False. The real tenant boundary is workspace
    # resolution (api_key/host/slug), not CORS.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(demo_request_router)
app.include_router(solutions_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(conversations_router)
app.include_router(saved_items_router)
app.include_router(appointments_router)
app.include_router(feedback_router)
app.include_router(notifications_router)
app.include_router(workspace_router)
app.include_router(agents_router)
app.include_router(escalation_router)
app.include_router(admin_workspaces_router)
app.include_router(admin_users_router)
app.include_router(knowledge_management_router)
app.include_router(org_signup_router)
app.include_router(invitations_router)
app.include_router(workspace_admins_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
