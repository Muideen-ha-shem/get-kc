from fastapi import APIRouter, HTTPException

from ...orchestrator.chat_orchestrator import chat_orchestrator
from ..schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        return chat_orchestrator.process_request_response(request.message)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to process chat request") from exc
