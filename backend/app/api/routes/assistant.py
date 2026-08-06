from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.agent.agent import SocietyAgent
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMMessage, LLMProvider

router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_llm_provider),
):
    agent = SocietyAgent(provider)
    history = [LLMMessage(role=m.role, content=m.content) for m in payload.history]

    reply = agent.run(
        db=db,
        resident=None,
        user_message=payload.message,
        history=history,
    )

    return ChatResponse(reply=reply)