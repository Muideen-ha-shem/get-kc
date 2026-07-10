from fastapi import APIRouter, HTTPException

from ..schemas import ChatRequest, ChatResponse
from ..services.generator import generate_answer
from ..services.retrieval import retrieve_context

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        matches, _, parent_urls = retrieve_context(request.message)
        if not matches:
            return ChatResponse(
                answer="I couldn’t find enough relevant context in the knowledge base for that question.",
                sources=[],
            )

        context_text = "\n".join(match.get("chunk_content", "") for match in matches if match.get("chunk_content"))
        result = generate_answer(request.message, context_text, parent_urls)
        return ChatResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to process chat request") from exc
