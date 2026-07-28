from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.appointments import router as appointments_router
from .routes.auth import router as auth_router
from .routes.chat import router as chat_router
from .routes.conversations import router as conversations_router
from .routes.demo_request import router as demo_request_router
from .routes.profile import router as profile_router
from .routes.saved_items import router as saved_items_router
from .routes.solutions import router as solutions_router

load_dotenv()

app = FastAPI(title="Ha-Shem RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
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


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
